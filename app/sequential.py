class LogicalPlanner:

    def __init__(self, operation, planning_svc):
        self.operation = operation
        self.planning_svc = planning_svc
        self.agent_svc = planning_svc.get_service('agent_svc')
        self.data_svc = planning_svc.get_service('data_svc')

    async def execute(self, phase):
        operation = (await self.data_svc.locate('operations', match=dict(name=self.operation.name)))[0]
        for member in operation.agents:
            for l in await self.planning_svc.select_links(operation, member, phase):
                await operation.apply(l)
