class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=(), ignore_enforcement_modules=()):
        self.operation = operation
        self.operation.ignore_enforcement_modules = ignore_enforcement_modules
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False

    async def execute(self, phase):
        for link in await self.planning_svc.get_links(operation=self.operation, phase=phase,
                                                      stopping_conditions=self.stopping_conditions, planner=self):
            await self.operation.apply(link)
