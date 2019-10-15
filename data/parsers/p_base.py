import re


class Relationship:

    def __init__(self, prop1, relation, prop2):
        self.prop1 = prop1
        self.relation = relation
        self.prop2 = prop2

    def get_relationship(self):
        return dict(prop1=self.prop1, relation=self.relation, prop2=self.prop2)


class BaseParser:

    @staticmethod
    def email(blob):
        """
        Parse out email addresses
        :param blob:
        :return:
        """
        return re.findall(r'[\w\.-]+@[\w\.-]+', blob)
