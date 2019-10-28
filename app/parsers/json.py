import json

from plugins.stockpile.app.parsers.base_parser import BaseParser
from plugins.stockpile.app.relationship import Relationship
from app.utility import logger


class Parser(BaseParser):

    def __init__(self, parser_info):
        self.logger = logger.Logger('parser.json')
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']

    def parse(self, blob):
        relationships = []

        data = json.loads(blob)

        self.logger.debug(data)
        for mp in self.mappers:
            self.logger.debug(mp)
            for match in self.key_search_generator(data, mp.get('property')):
                self.logger.debug(match)
                source = self.set_value(mp.get('source'), match, self.used_facts)
                target = self.set_value(mp.get('target'), match, self.used_facts)
                relationships.append(
                    Relationship(source=(mp.get('source'), source),
                                 edge=mp.get('edge'),
                                 target=(mp.get('target'), target))
                )
        return relationships

    def key_search_generator(self, json_input, lookup_key):
        if isinstance(json_input, dict):
            for k, v in json_input.items():
                if k == lookup_key:
                    yield v
                else:
                    for child_val in self.key_search_generator(v, lookup_key):
                        yield child_val
        elif isinstance(json_input, list):
            for item in json_input:
                for item_val in self.key_search_generator(item, lookup_key):
                    yield item_val

