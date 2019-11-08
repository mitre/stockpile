
class BaseRequirement:

    def __init__(self, requirement_info):
        self.enforcements = requirement_info['enforcements']

    def is_valid_relationship(self, used_facts, relationship):
        if not self._check_edge(relationship.edge):
            return False
        for fact in used_facts:
            if self._check_target(relationship.target, fact):
                return True
        return False

    """ PRIVATE """

    @staticmethod
    def _get_relationships(uf, relationships):
        return [r for r in relationships if r.source[0] == uf.trait and r.source[1] == uf.value]

    @staticmethod
    def _check_target(target, match):
        if target[0] == match.trait and target[1] == match.value:
            return True
        return False

    def _check_edge(self, edge):
        if edge == self.enforcements.edge:
            return True
        return False

