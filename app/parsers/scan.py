<<<<<<< HEAD
from app.objects.c_relationship import Relationship
from plugins.stockpile.app.parsers.base_parser import BaseParser
=======
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        for match in self.line(blob):
            values = match.split(':')
            for mp in self.mappers:
                relationships.append(
<<<<<<< HEAD
                    Relationship(source=(mp.source, values[0]),
                                 edge=mp.edge,
                                 target=(mp.target, values[1]))
=======
                    Relationship(source=Fact(mp.source, values[0]),
                                 edge=mp.edge,
                                 target=Fact(mp.target, values[1]))
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
                )
        return relationships
