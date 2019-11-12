import json

from app.objects.c_relationship import Relationship
from plugins.stockpile.app.parsers.base_parser import BaseParser
from app.utility.logger import Logger


class Parser(BaseParser):

    def __init__(self, parser_info):
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']
        self.log = Logger('parsing_svc')

    def parse(self, blob):
        relationships = []
        json_obj = self._load_json(blob)
        if json_obj is not None:
            for mp in self.mappers:
                json_key = mp.misc.get('json_key')
                if json_key is None:
                    self.log.warning("JSON Parser not given a 'json_key', not parsing")
                    continue
                for match in self._get_vals_from_json(json_obj, json_key):
                    source = self.set_value(mp.source, match, self.used_facts)
                    target = self.set_value(mp.target, match, self.used_facts)
                    relationships.append(
                        Relationship(source=(mp.source, source),
                                     edge=mp.edge,
                                     target=(mp.target, target))
                    )
        return relationships

    def _load_json(self, blob):
        try:
            return json.loads(blob)
        except Exception as error:
            self.log.warning("Output not JSON, use a different parser")
            return None

    def _get_vals_from_json(self, json_obj, key):
        """Get all values for a specified key recursively from JSON output."""
        if isinstance(json_obj, list):
            for item in json_obj:
                for res in self._get_vals_from_json(item, key):
                    yield res
        elif isinstance(json_obj, dict):
            for k, v in json_obj.items():
                if k == key:
                    yield json.dumps(v)
                if isinstance(v, list) or isinstance(v, dict):
                    for res in self._get_vals_from_json(v, key):
                        yield res
