from plugins.stockpile.app.requirements.base_requirement import BaseRequirement


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a link and the current operation, ensures that a the link does NOT contain any relationships
        that align with the enforcement mechanism
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        relationships = operation.all_relationships()
        for uf in link.used:
            if self.enforcements.source == uf.trait:
                for r in self._get_relationships(uf, relationships):
                    if self.is_valid_relationship([f for f in link.used if f != uf], r):
                        return False
        return True
