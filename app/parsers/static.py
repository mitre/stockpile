from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []

        for mp in self.mappers:
            source = mp.custom_parser_vals.get("source", None)
            target = mp.custom_parser_vals.get("target", source)

            if not source:
                continue

            source = self.set_value(mp.source, source, self.used_facts)
            target = self.set_value(mp.target, target, self.used_facts)
            relationships.append(
                Relationship(
                    source=Fact(mp.source, source),
                    edge=mp.edge,
                    target=Fact(mp.target, target),
                )
            )

        return relationships
