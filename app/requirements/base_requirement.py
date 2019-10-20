
class BaseRequirement:

    def __init__(self, requirement_info):
        self.enforcements = requirement_info['enforcements']

    def check_source_target(self, source, target):
        """
        Give a source and target fact, return True if the source and target comply with the enforcement mechanism and
        False if the source and target to don't comply. Also Return True if the source and target are of a type that the
        doesn't concern the enforcement mechanism
        :param source:
        :param target:
        :return:
        """
        if self._check_requirement_type(source, target):
            if self._is_valid_relationship(source, target):
                return True
            return False
        return True

    """ PRIVATE """

    def _check_requirement_type(self, source, target):
        if self.enforcements.get('source') == source.get('property') and self.enforcements.get('target') == \
                target.get('property'):
            return True
        return False

    def _is_valid_relationship(self, source, target):
        relationships = [relationship.get('target') for relationship in source.get('relationships', [])
                         if self.enforcements.get('edge') == relationship.get('edge')]
        for r in relationships:
            if target.get('value') == r.get('value'):
                return True
        return False
