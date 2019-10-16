from plugins.stockpile.data.parsers.p_base import BaseParser, Relationship


class EmailParser(BaseParser):

    def __init__(self, variables):
        self.user = variables.get('host.user.name')
        self.org = variables.get('target.org.name')

    def parse(self, blob):
        """
        Parse out email addresses
        :param blob:
        :return:
        """
        return [Relationship(prop1=m, relation=None, prop2=None) for m in self.email(blob)]
