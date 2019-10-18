

class Requirement():

    def __init__(self, requirement_info):
        self.enforcements = requirement_info['enforcements']
        self.fact_relationships = requirement_info['fact_relationships']

    def enforce(self, potential_fact, used_facts, all_operation_facts):
        """
        Given a potential fact, all facts used by the current link and all operation facts, determine if it complies
        with this fact relationships enforcement mechanism
        :param potential_fact: List of facts that are available
        :param used_facts
        :param all_operation_facts
        :return: True if it complies, False if it doesn't
        """
        for uf in used_facts:
            f = self._get_fact(all_operation_facts, uf)
            if self.enforcements.get('source') == f.get('property'):
                if self.enforcements.get('target') == potential_fact.get('property'):
                    for relationship in f.get('relationships'):
                        if self.enforcements.get('edge') == relationship.get('edge'):
                            if relationship.get('target').get('value') == potential_fact.get('value'):
                                return True
                            return False
        return True

    @staticmethod
    def _get_fact(fact_list, fact_id):
        for f in fact_list:
            if fact_id == f['id']:
                return f
