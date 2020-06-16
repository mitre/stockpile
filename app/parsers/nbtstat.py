<<<<<<< HEAD
from app.objects.c_relationship import Relationship
from plugins.stockpile.app.parsers.base_parser import BaseParser
=======
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser

>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
import re


class Parser(BaseParser):

    def __init__(self, parser_info):
<<<<<<< HEAD
=======
        super().__init__(parser_info)
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']

    def nbt_parser(self, text):
        if text and len(text) > 0:
            value = re.search(r'\s*(\S+)\s*<[0-9][0-9]>\s*GROUP', text)
            if value:
                return [value.group(1)]

    def parse(self, blob):
        relationships = []
        try:
            parse_data = self.nbt_parser(blob)
            for match in parse_data:
                for mp in self.mappers:
                    relationships.append(
<<<<<<< HEAD
                        Relationship(source=(mp.source, match),
                                     edge=mp.edge,
                                     target=(mp.target, None)
=======
                        Relationship(source=Fact(mp.source, match),
                                     edge=mp.edge,
                                     target=Fact(mp.target, None)
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
                                     )
                    )
        except Exception:
            pass
        return relationships
