from plugins.stockpile.app.requirements.base_requirements import BaseRequirement


class Requirement(BaseRequirement):

    def __init__(self, requirement_info):
        self.enforcements = requirement_info['enforcements']
        self.fact_relationships = requirement_info['fact_relationships']

    def enforce(self, fact_combinations):
        """
        Given a tuple combo of facts, list of fact relationships and a relationships requirement, prune all facts
        that don't comply
        :param combos: List of facts that are available
        :param fact_relationships: List of relationships
        :param relationship: Relationship object that has source
        :return: a list of combo tuples that comply with the relationship requirements
        """
        #facts = []
        # for i in range(len(fact_combinations) - 1):
        #     if self.get('property1') == fact_combo[i]['property'] \
        #             and relationship.get('property2') == fact_combo[i + 1]['property']:
        #         for r in operation['fact_relationships']:
        #             if fact_combo[i]['value'] == r['value1'] and fact_combo[i + 1]['value'] == r['value2'] \
        #                     and relationship['relationship'] == r['relationship']:
        #                 return True
        # return False
        return fact_combinations
