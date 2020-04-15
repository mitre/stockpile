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
        self.planning_svc.bucket_exhaustion('enumeration')
        self.next_bucket = self.planning_svc.default_next_bucket('enumeration', self.state_machine)

    async def goals(self):
        # use default logic -> exhaust all links in bucket
        self.planning_svc.bucket_exhaustion('goals')
        self.next_bucket = self.planning_svc.default_next_bucket('goals', self.state_machine)

    async def lateral_movement(self):
        # use default logic -> exhaust all links in bucket
        self.planning_svc.bucket_exhaustion('lateral_movement')
        self.next_bucket = self.planning_svc.default_next_bucket("lateral_movement", self.state_machine)

    async def misc(self):
        # use default logic -> exhaust all links in bucket
        self.plannin_svc.bucket_exhaustion('misc')
        self.next_bucket = None
