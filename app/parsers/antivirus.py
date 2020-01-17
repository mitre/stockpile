from app.objects.c_relationship import Relationship
from plugins.stockpile.app.parsers.base_parser import BaseParser


class Parser(BaseParser):

    ANTIVIRUS = ['symantec', 'norton']

    def parse(self, blob):
        relationships = []
        for match in self.line(blob.lower()):
            for uniform_match in [av for av in self.ANTIVIRUS if av in match]:
                for mp in self.mappers:
                    source = self.set_value(mp.source, uniform_match, self.used_facts)
                    relationships.append(Relationship(source=(mp.source, source)))
        return relationships
