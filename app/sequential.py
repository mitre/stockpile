class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['sequential']
        self.next_bucket = 'sequential'   # set first (and only) bucket to execute

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def sequential(self):
        for link in await self.planning_svc.get_links(operation=self.operation,
                                                      stopping_conditions=self.stopping_conditions,
                                                      planner=self):
            await self.operation.apply(link)
        self.next_bucket = None
        