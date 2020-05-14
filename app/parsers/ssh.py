import re

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        for ssh_cmd in re.findall(r'ssh.* (\w.+@\w.+)', blob):
            for mp in self.mappers:
                source = self.set_value(mp.source, ssh_cmd, self.used_facts)
                target = self.set_value(mp.target, ssh_cmd, self.used_facts)
                relationships.append(
                    Relationship(source=Fact(mp.source, source),
                                 edge=mp.edge,
                                 target=Fact(mp.target, target))
                )
        return relationships
