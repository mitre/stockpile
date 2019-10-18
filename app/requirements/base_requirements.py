from plugins.stockpile.app.relationship import Relationship


class BaseRequirement:

    @staticmethod
    def enforce(combos):
        """
        Given a tuple combo of facts, list of fact relationships and a relationships requirement, prune all facts
        that don't comply
        :param combos: List of facts that are available
        :param fact_relationships: List of relationships
        :param relationship: Relationship object that has source
        :return: a list of combo tuples that comply with the relationship requirements
        """
        facts = []
        for combo in combos:
            facts.append(combo)
        return facts