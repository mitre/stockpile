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
            port = self._locate_port(match)
            if port:
                for mp in self.mappers:
                    source = self.set_value(mp.source, port, self.used_facts)
                    target = self.set_value(mp.target, port, self.used_facts)
                    relationships.append(
<<<<<<< HEAD
                        Relationship(source=(mp.source, source),
                                     edge=mp.edge,
                                     target=(mp.target, target))
=======
                        Relationship(source=Fact(mp.source, source),
                                     edge=mp.edge,
                                     target=Fact(mp.target, target))
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
                    )
        return relationships

    @staticmethod
    def _locate_port(line):
        try:
            if 'open' in line:
                port = line.split()[0].split('/')[0]
                return int(port)
        except Exception:
            pass
        return None
