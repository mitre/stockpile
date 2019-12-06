class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=[]):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions

    async def execute(self, phase):
        for link in await self.planning_svc.get_links(operation=self.operation, phase=phase):
            if await self.planning_svc.check_stopping_conditions(self.operation, self.stopping_conditions):
                return
            await self.operation.apply(link)
