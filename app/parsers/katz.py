from plugins.stockpile.app.parsers.base_parser import BaseParser
from plugins.stockpile.app.relationship import Relationship

import re
from collections import defaultdict

class MimikatzBlock(object):
    def __init__(self):
        self.session = ""
        self.username = ""
        self.domain = ""
        self.logon_server = ""
        self.logon_time = ""
        self.sid = ""
        self.packages = defaultdict(list)


class Katz(BaseParser):
    def __init__(self, parser_info):
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']
        self.parse_base = 'wdigest'

    def parse_kats(self, output):
        """
        Parses mimikatz output with the logonpasswords command and returns a list of dicts of the credentials.
        Args:
            output: stdout of "mimikatz.exe privilege::debug sekurlsa::logonpasswords exit"
        Returns:
            A list of MimikatzSection objects
        """
        # split sections using "Authentication Id" as separator
        sections = output.split("Authentication Id")
        creds = []
        for section in sections[1:]:
            mk_section = MimikatzBlock()
            package = {}
            package_name = ""
            in_header = True
            for line in section.splitlines():
                line = line.strip()
                if in_header:
                    if line.startswith('msv'):
                        in_header = False
                    else:
                        session = re.match(r"^\s*Session\s*:\s*([^\r\n]*)", line)
                        if session:
                            mk_section.session = session.group(1)
                        username = re.match(r"^\s*User Name\s*:\s*([^\r\n]*)", line)
                        if username:
                            mk_section.username = username.group(1)
                        domain = re.match(r"^\s*Domain\s*:\s*([^\r\n]*)", line)
                        if domain:
                            mk_section.domain = domain.group(1)
                        logon_server = re.match(r"^\s*Logon Server\s*:\s*([^\r\n]*)", line)
                        if logon_server:
                            mk_section.logon_server = logon_server.group(1)
                        logon_time = re.match(r"^\s*Logon Time\s*:\s*([^\r\n]*)", line)
                        if logon_time:
                            mk_section.logon_time = logon_time.group(1)
                        sid = re.match(r"^\s*SID\s*:\s*([^\r\n]*)", line)
                        if sid:
                            mk_section.sid = sid.group(1)
                        continue

                if line.startswith('['):
                    # this might indicate the start of a new account
                    if 'Username' in package and package['Username'] != '(null)' and \
                            (('Password' in package and package['Password'] != '(null)') or 'NTLM' in package):
                        mk_section.packages[package_name].append(package)

                    # reset the package
                    package = {}
                    pass
                elif line.startswith('*'):
                    m = re.match(r"\s*\* (.*?)\s*: (.*)", line)
                    if m:
                        package[m.group(1)] = m.group(2)

                elif line:
                    # parse out the new section name
                    match_group = re.match(r"([a-z]+) :", line)
                    if match_group:
                        # this is the start of a new ssp
                        # save the current ssp if necessary
                        if 'Username' in package and package['Username'] != '(null)' and \
                                (('Password' in package and package['Password'] != '(null)') or 'NTLM' in package):
                            mk_section.packages[package_name].append(package)

                        # reset the package
                        package = {}

                        # get the new name
                        package_name = match_group.group(1)

            # save the current ssp if necessary
            if 'Username' in package and package['Username'] != '(null)' and \
                    (('Password' in package and package['Password'] != '(null)') or 'NTLM' in package):
                mk_section.packages[package_name].append(package)

            # save this section
            if mk_section.packages:
                creds.append(mk_section)

        return creds

    def parse(self, blob):
        relationships = []
        parse_data = self.parse_kats(blob)
        for match in parse_data:
            if self.parse_mode in match.packages:
                for mp in self.mappers:
                    relationships.append(
                        Relationship(source=(mp.get('source'), match.package[self.parse_mode]['Username']),
                                     edge=mp.get('edge'),
                                     target=(mp.get('target'), match.package[self.parse_mode]['Password']))
                    )
        return relationships

