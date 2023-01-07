from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


GPU_TOKEN = ": "


class Parser(BaseParser):
    """A parser for extracting the GPUs found on a Linux system"""

    def parse(self, blob):
        relationships = []
        for match in self.line(blob):
            gpu = self._locate_gpu(match)
            if gpu:
                for mp in self.mappers:
                    source = self.set_value(mp.source, gpu, self.used_facts)
                    target = self.set_value(mp.target, gpu, self.used_facts)
                    relationships.append(
                        Relationship(source=Fact(mp.source, source),
                                     edge=mp.edge,
                                     target=Fact(mp.target, target))
                    )
        return relationships

    @staticmethod
    def _locate_gpu(line):
        try:
            if GPU_TOKEN in line:
                gpu = line.split(GPU_TOKEN)[1]
                return gpu
        except Exception:
            pass
        return None
