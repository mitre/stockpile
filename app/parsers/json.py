from app.objects.c_relationship import Relationship
from plugins.stockpile.app.parsers.base_parser import BaseParser
import json


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        try:
            json_obj = json.loads(blob)
        except Exception as error:
            self.log.warning("Output not JSON, use a different parser")
            return []
        for mp in self.mappers:
            json_key = mp.misc.get('json_key')
            if not json_key:
                self.log.warning("JSON Parser not given a 'json_key', not parsing")
                continue
            for match in self.get_vals_from_json(json_obj, json_key):
                source = self.set_value(mp.source, match, self.used_facts)
                target = self.set_value(mp.target, match, self.used_facts)
                relationships.append(
                    Relationship(source=(mp.source, source),
                                 edge=mp.edge,
                                 target=(mp.target, target))
                )
        return relationships

    def get_vals_from_json(self, json_obj, key):
        if isinstance(json_obj, list):
            for item in json_obj:
                for res in self.get_vals_from_json(item, key):
                    yield res
        elif isinstance(json_obj, dict):
            for k, v in json_obj.items():
                if k == key:
                    yield json.dumps(v)
                if isinstance(v, list) or isinstance(v, dict):
                    for res in self.get_vals_from_json(v, key):
                        yield res
