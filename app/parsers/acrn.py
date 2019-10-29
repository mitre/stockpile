from plugins.stockpile.app.parsers.base_parser import BaseParser
from plugins.stockpile.app.relationship import Relationship


class Parser(BaseParser):

    def __init__(self, parser_info):
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']

    def parse(self, blob):
        relationships = []
        vm_names = self._get_vm_names(blob)
        for name in vm_names:
            for mp in self.mappers:
                relationships.append(
                    Relationship(source=(mp.get('source'), name),
                                 edge=mp.get('edge'),
                                 target=(mp.get('target'), None))
                )
        return relationships

    ''' PRIVATE '''

    def _get_vm_names(self, blob):
        vm_names = []
        index = 0
        for line in blob.split('\n'):
            if 'VM NAME' in line:
                index = line.index('VM ID')
                continue
            if '=====' in line:
                continue
            if len(line) > 0:
                vm_names.append(line[0:index].strip())
        return vm_names
