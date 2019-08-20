class LogicalPlanner:

    def __init__(self, services, **params):
        self.data_svc = services.get('data_svc')
        self.planning_svc = services.get('planning_svc')

    async def execute(self, operation, phase):
        for member in operation['host_group']:
            for l in await self.planning_svc.select_links(operation, member, phase):
                l.pop('rewards', [])
                await self.data_svc.create_link(l)
        await self.planning_svc.wait_for_phase(operation)
