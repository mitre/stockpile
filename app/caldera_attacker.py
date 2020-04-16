class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['enumeration', 'goals', 'lateral_movement', 'misc']
        self.next_bucket = 'enumeration'   # set first bucket to execute

    async def enumeration(self):
        # use default logic -> exhaust all links in bucket
        await self.planning_svc.bucket_exhaustion('enumeration', self.operation)
        self.next_bucket = await self.planning_svc.default_next_bucket('enumeration', self.state_machine)

    async def goals(self):
        # use default logic -> exhaust all links in bucket
        goal = 'collection'  # 'impact', 'exfiltration' 
        await self.planning_svc.bucket_exhaustion(goal, self.operation)
        self.next_bucket = await self.planning_svc.default_next_bucket('goals', self.state_machine)

    async def lateral_movement(self):
        # use default logic -> exhaust all links in bucket
        await self.planning_svc.bucket_exhaustion('lateral_movement', self.operation)
        self.next_bucket = await self.planning_svc.default_next_bucket("lateral_movement", self.state_machine)

    async def misc(self):
        # use default logic -> exhaust all links in bucket
        await self.planning_svc.bucket_exhaustion('misc', self.operation)
        self.next_bucket = None
