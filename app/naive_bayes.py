from . import NB_Model_Class
# import NB_Model_Class

class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['bayes_state']
        self.next_bucket = 'bayes_state'   # repeat this bucket until we run out of links.
        # holder for Naive Bayes probability object
        self.NB_probability_obj = None
        print("NB Planner Initialized")

    async def execute(self):
        # if operation data and probabilities not setup
        if self.NB_probability_obj is None:
            print("Begin NB Class Startup Operations")
        #     # create Naive Bayes probability object, and pass data_svc object
            self.NB_probability_obj = NB_Model_Class.NBLinkProbabilities(self.planning_svc.get_service('data_svc'))
        #     # await necessary API calls + df building
            print("Inititalized Class")
            await self.NB_probability_obj.startup_operations()

            print("Startup Operations Completed")

        # execute main state of planner
        await self.planning_svc.execute_planner(self)

    async def bayes_state(self):

        print("BAYES STATE")

        links_to_use = []

        # Get the first available link for each agent (make sure we maintain the order).
        for agent in self.operation.agents:
            possible_agent_links = await self._get_links(agent=agent)
            print("Possible Agent Links")
            print(possible_agent_links)
            next_link = await self._get_best_link(possible_agent_links)
            if next_link:
                links_to_use.append(await self.operation.apply(next_link))

        if links_to_use:
            # Each agent will run the next available step.
            await self.operation.wait_for_links_completion(links_to_use)
        else:
            # No more links to run.
            self.next_bucket = None

    async def _get_links(self, agent=None):
        return await self.planning_svc.get_links(operation=self.operation, agent=agent)

    # Given list of links, returns the link with the highest probability of success
    # that meets user criteria on required data and visibility.
    # If no such link exists then return None
    async def _get_best_link(self, links):
        print("IN GET BEST LINKS")
        print(links)
        # confirm class has necessary data
        # link to prob success dict
        # query probability of each link and store
        # iterate through links and select best
        # return best link

        abil_id_to_link = dict()
        for link in links:
            abil_id_to_link[link.ability.ability_id] = link
        candidate_ids = set(abil_id_to_link.keys())
        for ab_id in self.operation.adversary.atomic_ordering:
            if ab_id in candidate_ids:
                return abil_id_to_link[ab_id]
