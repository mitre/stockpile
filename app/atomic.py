class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['atomic']
        self.next_bucket = 'atomic'   # repeat this bucket until we run out of links.

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def atomic(self):
        links_to_use = []

        all_agents_links = await self._get_links()
        for agent, possible_links in all_agents_links.items():
            next_link = await self._get_next_atomic_link(possible_links)
            if next_link:
                links_to_use.append(await self.operation.apply(next_link))

        if links_to_use:
            # Each agent will run the next available step.
            await self.operation.wait_for_links_completion(links_to_use)
        else:
            # No more links to run.
            self.next_bucket = None

    async def _get_links(self):
        return await self.planning_svc.get_links(operation=self.operation)

    # Given list of links, returns the link that appears first in the adversary's atomic ordering.
    async def _get_next_atomic_link(self, links):
        abil_id_to_link = dict()
        for link in links:
            abil_id_to_link[link.ability.ability_id] = link
        candidate_ids = set(abil_id_to_link.keys())
        for ab_id in self.operation.adversary.atomic_ordering:
            if ab_id in candidate_ids:
                return abil_id_to_link[ab_id]
