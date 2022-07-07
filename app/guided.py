
import collections
import copy
import heapq
import itertools
import re

import networkx as nx

from app.objects.c_ability import Ability
from app.objects.c_agent import Agent
from app.objects.secondclass.c_goal import Goal


NONLIMITED_FACT_REGEX = r'#{(.*?)}'
LIMITED_FACT_REGEX = r'(.*?)\['
EXHAUSTION_KEY = 'exhaustion'

DEFAULT_HALF_LIFE_PENALTY=4
DEFAULT_HALF_LIFE_GAIN=2
DEFAULT_GOAL_ACTION_DECAY=2
DEFAULT_GOAL_WEIGHT=1
DEFAULT_FACT_SCORE_WEIGHT=0


class LogicalPlanner:
    """
    The guided planner makes use of distance to goals in a dependency graph to select the optimal next action.

    On operation start:
    1. Identify the set of goal fact types that we're looking for

    2. Compute the distance score for each ability
        -- Defined as the shortest distance -- measured in actions -- between each ability and a goal fact type
            -- To compute this, we usually have to compute (in some way) the underlying attack graph
            -- If an action has two paths to a goal fact types, choose the /shortest/
            -- An action that immediately leads to a goal fact type gets a score of 0
            -- An action that leads to an action that leads to a goal fact type gets a score of 1, etc.
        -- Distance scores should be /reversed/ so that "goal actions" -- i.e., those initially with 0 -- get the /biggest/ score
            -- Compute the distance score as per the step above and find the ability with the largest score (i.e., the longest path to a goal)
            -- Set each ability's updated score the "abs(cur_score - max_score)" to reverse it

    3. Initialize needed variables:
        -- half_life_penalty: how much we penalize an action for not being helpful
        -- half_life_gain: how much we passively increase each action's score
        -- goal_action_decay: how much we deprioritize a specific goal action
            -- Note: we define a "goal action" as an action that leads to a goal fact type
        -- goal_weight: how much we "weigh" the action's distance to a goal
        -- fact_score_weight: how much we weigh the action's constituent facts
        -- absolute_distance: the distance table computed in step 2
        -- effective_distance: will store the /decaying/ distance, but is initialized to be equal to absolute distance
            -- Sometimes we call this "last distance"


    On action selection:
    4. Update the effective distance of each action
        -- The formula is as follows: effective_distance(A)' = effective_distance(A) + (absolute_distance(A) - effective_distance(A))/half_life_gain

    5. Get all grounded links

    6. Penalize the last action executed if it did not bring us closer to the goal
        -- If the last action was not a goal action:
            -- Find the current max reward by iterating through each ability from step 5 and recording the /absolute_distance/ of that ability
            -- If 'max_reward > absolute_distance(last_action)' that means that we're now closer to the goal
                -- For this case, we "reset" the effective distance of the last action: 'effective_distance(last_action) = absolute_distance(last_action)'
            -- Otherwise, we didn't make progress, so we need to penalize the last action
                -- To do this, we do: effective_distance(last_action) = effective_distance(last_action)/half_life_penalty
        -- If the last action was a goal action:
            -- We want to "decentivize" this action to avoid local optima (i.e., so it doesn't always execute the same goal action repeatedly and it pursues other goals)
            -- Computed as: effective_distance(A) = max_value - 1 + (effective_distance(A) + 1 - max_value)/goal_action_decay
            -- Note that max_value is defined as the largest value in absolute_distance
            -- What this does is this makes sure that the goal action's score is always between (max_value) and (max_value - 1) so it will /always/ be prioritized over normal actions

    7. Select the action with the highest score -- execute it and parse results
        -- An action's score is the weighted sum of its fact score + its distance score
        -- score(A) = goal_weight * effective_distance(A) + fact_score_weight * fact_score(A)
        -- Note that fact score is the normal fact score from the reward planner

    8. Determine if we've satisfied our goals:
        8a) If we've now satisfied all of our goals, terminate
        8b) If we've satisfied a goal, but other goals remain, re-run step 2, reset effective_distance, and return to step 4
        8c) If we haven't made any changes to our goals, return to step 4
    """

    def __init__(
        self, 
        operation, 
        planning_svc, 
        stopping_conditions=(), 
        half_life_penalty=DEFAULT_HALF_LIFE_PENALTY,
        half_life_gain=DEFAULT_HALF_LIFE_GAIN,
        goal_action_decay=DEFAULT_GOAL_ACTION_DECAY,
        goal_weight=DEFAULT_GOAL_WEIGHT,
        fact_score_weight=DEFAULT_FACT_SCORE_WEIGHT
    ):
        """
        :param operation:
        :param planning_svc:
        :param stopping_conditions:
        :param half_life_penalty: Weight to penalize an action for not being helpful.
        :param half_life_gain: Weight to passively increase each action's score.
        :param goal_action_decay: Weight to deprioritize a specific goal action.
        :param goal_weight: Weight for the action's distance to a goal.
        :param fact_score_weight: Weight for the action's constituent facts.
        """
        self.operation = operation
        self.planning_svc = planning_svc
        self.data_svc = planning_svc.get_service('data_svc')
        self.goals = operation.objective.goals
        self.abilities = operation.adversary.atomic_ordering

        self.half_life_penalty = half_life_penalty
        self.half_life_gain = half_life_gain
        self.goal_action_decay = goal_action_decay
        self.goal_weight = goal_weight
        self.fact_score_weight = fact_score_weight
        self.last_action = None
        self.goal_actions = set()

        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['guided']
        self.next_bucket = 'guided'

    async def execute(self):
        await self.planning_svc.execute_planner(self)
    
    async def guided(self):
        await self.execute_subop(abilities=self.abilities, goals=self.goals)

    async def execute_subop(self, abilities, agent=None, goals=[]):
        """
        :param abilities: List of ability IDs to plan with.
        :param agent: Agent to focus planning on. If no agent is provided, planning will focus on all agents available in the operation.
        :param goals: List of Goal objects to plan towards. Providing an empty list or an Exhaustion goal will cause the planner to infer goals from the ability's dependency graph.
        """
        attack_graph = await self._build_attack_graph(abilities, agent)

        if len(goals) == 0 or goals[0].target == EXHAUSTION_KEY:
            planner_goals = await self._create_terminal_goals(attack_graph)
        else:
            planner_goals = goals[:]

        await self._show_attack_graph(attack_graph) # TODO: Remove before merging, just for debug purposes

        absolute_distance_table = await self._build_distance_table(attack_graph, goals=planner_goals)
        effective_distance_table = copy.deepcopy(absolute_distance_table)

        goal_links = await self._get_goal_links(absolute_distance_table, agent=agent)
        while len(planner_goals) > 0 and len(goal_links) > 0:
            tasked_links = await self._task_agents(goal_links, effective_distance_table, abilities, agent=agent)

            await self.operation.wait_for_links_completion(tasked_links)
            
            current_goal_count = len(planner_goals)
            planner_goals = await self._update_goals(current_goals=planner_goals)
            if len(planner_goals) < current_goal_count:
                absolute_distance_table, effective_distance_table = await self._handle_goal_achieved(attack_graph, goals=planner_goals)
            else:
                effective_distance_table = await self._handle_no_goal_achieved(absolute_distance_table,
                                                                                effective_distance_table,
                                                                                goal_links)
            goal_links = await self._get_goal_links(absolute_distance_table, agent=agent)

        if not len(goal_links) or not len(planner_goals):
            self.planning_svc.log.debug('No more links available or all goals satisfied, planner complete.')
            self.next_bucket = None

    """ PRIVATE """

    async def _build_attack_graph(self, abilities, agent):
        """
        Produces a directed graph that includes nodes for each ability, and nodes of each input and output fact
        of those abilities.
        """
        attack_graph = nx.DiGraph()
        for ability_id in abilities:
            for ability in await self.data_svc.locate('abilities', dict(ability_id=ability_id)):
                if agent:
                    attack_graph = await self._output_fact_edges(ability, attack_graph, agent)
                    attack_graph = await self._input_fact_edges(ability, attack_graph, agent)
                else:
                    for operation_agent in self.operation.agents:
                        attack_graph = await self._output_fact_edges(ability, attack_graph, operation_agent)
                        attack_graph = await self._input_fact_edges(ability, attack_graph, operation_agent)
        return attack_graph

    async def _output_fact_edges(self, ability, graph, agent):
        """
        Adds output facts to a directed graph based on the parserconfigs included in an ability.
        """
        executor = await agent.get_preferred_executor(ability)
        for parser in executor.parsers:
            for parserconfig in parser.parserconfigs:
                graph.add_edge(ability, parserconfig.source)
                if parserconfig.target:
                    graph.add_edge(ability, parserconfig.target)
                if parserconfig.edge:
                    graph.add_edge(ability, parserconfig.edge)
        return graph

    async def _input_fact_edges(self, ability, graph, agent):
        """
        Adds input facts to a directed graph based on the facts present in a command template.
        """
        def add_to_graph(fact):
            if fact not in list(Agent.RESERVED):
                graph.add_edge(fact, ability)

        executor = await agent.get_preferred_executor(ability)
        for fact in re.findall(NONLIMITED_FACT_REGEX, executor.test, flags=re.DOTALL):
            nonlimited = re.search(LIMITED_FACT_REGEX, fact)
            if nonlimited:
                add_to_graph(nonlimited.group(0)[:-1])
            else:
                add_to_graph(fact)
        return graph

    async def _create_terminal_goals(self, attack_graph):
        """
        Infers goals based on which nodes in a directed graph have an outward degreee of zero.
        """
        terminal_nodes = [node for node, degree in attack_graph.out_degree() if degree == 0]
        aggregated_goals = collections.Counter(terminal_nodes)
        goals = [Goal(target=trait, operator='*', count=count) for trait, count in aggregated_goals.items()]
        return goals

    async def _build_distance_table(self, graph, goals):
        """
        Constructs a table of shortest distance from each ability to one of the goals. The weights get
        inverted, so the highest score in the table is the closest action to a goal.
        """
        ability_distances = dict()
        self.goal_actions = set()
        max_dist = 0

        for goal in goals:
            shortest_path = nx.shortest_path(graph, target=goal.target)

            for node, path in shortest_path.items():
                filtered_path = [n for n in path if isinstance(n, Ability)]
                path_distance = len(filtered_path)

                if not isinstance(node, Ability):
                    continue

                if path_distance == 1:
                    self.goal_actions.add(node.ability_id)

                if path_distance > max_dist:
                    max_dist = path_distance

                if node.ability_id in ability_distances and path_distance > ability_distances[node.ability_id]:
                    continue

                ability_distances[node.ability_id] = path_distance

        for ab, length in ability_distances.items():
            ability_distances[ab] = abs(length - max_dist) + 1

        return ability_distances

    async def _handle_goal_achieved(self, attack_graph, goals=None):
        """
        Rebuilds the distance table based on a revised set of goals.
        """
        absolute_distance_table = await self._build_distance_table(attack_graph, goals=goals)
        effective_distance_table = copy.deepcopy(absolute_distance_table)
        return absolute_distance_table, effective_distance_table

    async def _handle_no_goal_achieved(self, absolute_dist_table, effective_dist_table, goal_links):
        """
        Penalizes the weights in the current effective distance table to keep the planner out of endless loops.
        """
        executable_link_max_val = max(absolute_dist_table[l.ability.ability_id] for l in goal_links)
        last_action_effective_score = effective_dist_table[self.last_action.ability_id]
        last_action_absolute_score = absolute_dist_table[self.last_action.ability_id]
        effective_dist_table[self.last_action.ability_id] = self._apply_effective_distance_penalty(
            last_action_effective_score, last_action_absolute_score, executable_link_max_val)

        for ability_id, score in effective_dist_table.items():
            effective_dist_table[ability_id] = score + float(absolute_dist_table[ability_id] - score) / \
                                               self.half_life_gain
        return effective_dist_table

    def _apply_effective_distance_penalty(self, effective_score, absolute_score, max_value):
        """
        Calculates the new effective distance for the last action performed.
        """
        if self.last_action.ability_id in self.goal_actions:
            new_distance = max_value - 1 + float(effective_score + 1 - max_value) / self.goal_action_decay  # Action was a goal action, decentivize this action to avoid local optimia
        elif max_value > abs(absolute_score):
            new_distance = absolute_score   # we're now closer to our goal, reset the effective distance of the last action
        else:
            new_distance = float(effective_score) / self.half_life_penalty
        
        return new_distance

    async def _get_goal_links(self, absolute_distance_table, agent=None):
        """
        Produces all links for abilities that are present in the absolute distance table.
        """
        links = await self.planning_svc.get_links(self.operation, agent=agent)
        return [link for link in links if link.ability.ability_id in absolute_distance_table]

    async def _task_agents(self, links, link_distance_table, abilities, agent=None):
        """
        Chooses next actions for agent provided. If no agent is provided, then the method will choose and return
        next actions for all agents in the operation.
        """
        tasked_link_ids = []
        if agent:
            agent_links = [link for link in links if link.paw == agent.paw]
            if len(agent_links):
                tasked_link = await self._task_best_action(agent_links, link_distance_table, abilities)
                tasked_link_ids.append(tasked_link.id)
        else:
            for operation_agent in self.operation.agents:
                agent_links = [link for link in links if link.paw == operation_agent.paw]
                if not len(agent_links):
                    continue
                tasked_link = await self._task_best_action(agent_links, link_distance_table, abilities)
                tasked_link_ids.append(tasked_link.id)

        return tasked_link_ids

    async def _task_best_action(self, agent_links, link_distance_table, abilities):
        """
        Produces the best available link based on the current distance table. The method also applies links
        that support the chosen link, but that do not actively work towards the goal.
        """
        async def _heapsort(links):
            sorted_links = []
            counter = itertools.count()
            for _, (dist, link) in links.items():
                entry = [-dist, -link.score, next(counter), link]
                heapq.heappush(sorted_links, entry)
            return [heapq.heappop(sorted_links)[3] for _ in range(len(sorted_links))]

        weighted_scores = {link.id: ((link_distance_table[link.ability.ability_id] * self.goal_weight + 
                                      link.score * self.fact_score_weight), link) for link in agent_links}
        sorted_links = await _heapsort(weighted_scores)
        link_to_execute = sorted_links[0]

        supporting_links = await self._get_supporting_links(link_to_execute, abilities)
        for supporting_link in supporting_links:
            await self.operation.apply(supporting_link)
        await self.operation.apply(link_to_execute)
        self.last_action = link_to_execute.ability
        return link_to_execute

    async def _get_supporting_links(self, link, abilities):
        """
        Method to create all links for abilities that have zero output edges and appear earlier in the atomic ordering
        than the chosen action.
        """
        async def has_output_facts(ability, agent):
            executor = await agent.get_preferred_executor(ability)
            for parser in executor.parsers:
                if parser.parserconfigs:
                    return True
            return False
        
        def get_list_index(item, list_):
            if item not in list_:
                return -1
            for i, value in enumerate(list_):
                if value == item:
                    return i

        if self.last_action:
            last_ability_index = get_list_index(self.last_action.ability_id, abilities)
        else:
            last_ability_index = 0
        link_ability_index = get_list_index(link.ability.ability_id, abilities)

        agent = (await self.data_svc.locate('agents', match=dict(paw=link.paw)))[0]
        links = await self.planning_svc.get_links(self.operation, agent=agent)
        connecting_abilities = abilities[last_ability_index:link_ability_index]
        connecting_abilities = await self.data_svc.locate('abilities', match=dict(ability_id=tuple(connecting_abilities)))
        connecting_abilities = [ability for ability in connecting_abilities if not await has_output_facts(ability, agent)]
        supporting_links = [l for ability in connecting_abilities for l in links if l.ability == ability]

        return supporting_links

    async def _update_goals(self, current_goals):
        """
        Removes goals from the set that have been successfully accomplished.
        """
        remaining_goals = []
        for goal in current_goals:
            goal_found = False
            if goal.satisfied(await self.operation.all_facts()):
                goal_found = True
                self.planning_svc.log.debug(f'Goal {goal.target} {goal.operator} {goal.value} accomplished!')
            if not goal_found and len(current_goals) > 0:
                remaining_goals.append(goal)
        return remaining_goals

    async def _show_attack_graph(self, g):
        """DEBUG function -
        convert graph to human readable/useful nodes and pop-up window

        WARN: matplotlib will create a deluge of debug messages.
        """
        from pathlib import Path
        import matplotlib.pyplot as plt
        PDF_FILE = Path.home().joinpath('guided_attack_graph.pdf')
        g_c = nx.DiGraph()
        for e in g.edges:
            s, t = e
            if not isinstance(s, str):
                s = '{}:{}'.format(s.ability_id[:7] + "..", s.name)
            if not isinstance(e[1], str):
                t = '{}:{}'.format(t.ability_id[:7] + "..", t.name)
            g_c.add_edge(s, t)
        pos = nx.spring_layout(g_c, k=0.60, iterations=30)
        nx.draw(g_c,
                pos=pos,
                with_labels=True,
                node_color='red',
                edge_color='black',
                font_weight='bold')
        plt.savefig(PDF_FILE)
