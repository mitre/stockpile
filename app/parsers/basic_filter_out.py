from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser

import re


class Parser(BaseParser):
    """Base filter out parser

    NOTE: Not to be used directly but inherited and regexs defined.
    """
    def __init__(self, parser_info, regexs=None):
        super().__init__(parser_info)
        self.filter_out = regexs
    
    def parse(self, blob):
        relationships = []
        for line in self.line(blob):
            for filter_ in self.filter_out:
                if re.match(filter_, line):
                    continue
                for mp in self.mappers:
                    source = self.set_value(mp.source, line, self.used_facts)
                    target = self.set_value(mp.target, line, self.used_facts)
                    relationships.append(
                        Relationship(source=Fact(mp.source, source),
                                    edge=mp.edge,
                                    target=Fact(mp.target, target))
                    )
        return relationships
