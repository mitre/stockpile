<<<<<<< HEAD
from app.objects.c_relationship import Relationship
from plugins.stockpile.app.parsers.base_parser import BaseParser
from app.utility.logger import Logger
=======
import logging

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be


class Parser(BaseParser):

    def __init__(self, parser_info):
<<<<<<< HEAD
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']
        self.log = Logger('Parser')
=======
        super().__init__(parser_info)
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']
        self.log = logging.getLogger('Parser')
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be

    def gd_parser(self, text):
        results = dict()

<<<<<<< HEAD
        for block in text.split('\r\n\r\n'):
=======
        chunks = text.split('\n\n')
        if text.find('\r') != -1:
            chunks = text.split('\r\n\r\n')
        for block in chunks:
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
            if block:
                hostname = None
                pvi = None
                for line in block.splitlines():
                    hostname = self._parse_hostname(line, hostname)
                    pvi = self._parse_version(line, pvi)
                    if line.startswith('Exception') and '(0x80005000)' in line:
                        # Domain communication error
                        self.log.warning('Get-Domain parser: Domain Issue 0x80005000: Verify that the rat is running '
                                         'under a Domain Account, and that the Domain Controller can be reached.')
                if hostname and pvi:
                    results[hostname] = dict(parsed_version_info=pvi)
        if not results:
            self.log.warning('Get-Domain Parser: Returned data contained no parseable information!')
        return results

    def parse(self, blob):
        relationships = []
        try:
            parse_data = self.gd_parser(blob)
            for match in parse_data:
                for mp in self.mappers:
                    relationships.append(
<<<<<<< HEAD
                        Relationship(source=(mp.source, match),
                                     edge=mp.edge,
                                     target=(mp.target, None)))
=======
                        Relationship(source=Fact(mp.source, match),
                                     edge=mp.edge,
                                     target=Fact(mp.target, None)))
>>>>>>> a2b4f2d02f7a96ebd241898b844e9a36dfccc6be
        except Exception as error:
            self.log.warning('Get-Domain parser encountered an error - {}. Continuing...'.format(error))
        return relationships

    '''    PRIVATE FUNCTION     '''

    @staticmethod
    def _parse_hostname(line, current):
        if line.startswith('dnshostname'):
            field_name, value = [c.strip() for c in line.split(':')]
            return value.lower()
        return current

    @staticmethod
    def _parse_version(line, current):
        if line.startswith('operatingsystemversion'):
            value = line.split(':')[-1].strip()  # Looks like: '10.0 (14393)'
            os_version, build_number = value.split(' ')
            build_number = build_number[1:-1]  # remove parens
            major_version, minor_version = os_version.split('.')
            return dict(os_name='windows', major_version=major_version,
                        minor_version=minor_version, build_number=build_number)
        return current
