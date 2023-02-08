from plugins.stockpile.app.requirements.base_requirement import BaseRequirement


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a link and the current operation, check that the operation's knowledge base contains
        at least one fact (and edge) that complies with the requirement.
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        facts = await operation.all_facts()
        filtered_facts = [fact for fact in facts if fact.trait == self.enforcements['source'] and
                                                    link.paw in fact.collected_by]
        if self.enforcements.get('edge', None):
            filtered_facts = [fact for fact in filtered_facts if self._in_substring(self.enforcements['edge'], fact.relationships)]
        if len(filtered_facts) > 0:
            return True
        return False

    def _in_substring(self, key, string_list):
        return any(key in string for string in string_list)
