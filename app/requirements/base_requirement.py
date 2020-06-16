<<<<<<< HEAD

=======
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
class BaseRequirement:

    def __init__(self, requirement_info):
        self.enforcements = requirement_info['enforcements']

    def is_valid_relationship(self, used_facts, relationship):
        """
        Checks if the used facts for a link match with the list of known fact relationships
        :param used_facts:
        :param relationship:
        :return: True if there is a match, False if not
        """
        if not self._check_edge(relationship.edge):
            return False
<<<<<<< HEAD
        for fact in used_facts:
            if self._check_target(relationship.target, fact):
                return True
        return False
=======
        if 'target' in self.enforcements.keys():
            for fact in used_facts:
                if self._check_target(relationship.target, fact):
                    return True
            return False
        return True
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be

    """ PRIVATE """

    @staticmethod
    def _get_relationships(uf, relationships):
<<<<<<< HEAD
        return [r for r in relationships if r.source[0] == uf.trait and r.source[1] == uf.value]

    @staticmethod
    def _check_target(target, match):
        if target[0] == match.trait and target[1] == match.value:
=======
        return [r for r in relationships if r.source.trait == uf.trait and r.source.value == uf.value]

    @staticmethod
    def _check_target(target, match):
        if target.trait == match.trait and target.value == match.value:
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
            return True
        return False

    def _check_edge(self, edge):
<<<<<<< HEAD
        if edge == self.enforcements.edge:
=======
        if edge == self.enforcements['edge']:
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
            return True
        return False
