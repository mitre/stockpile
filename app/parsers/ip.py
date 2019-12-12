from app.objects.c_relationship import Relationship
from plugins.stockpile.app.parsers.base_parser import BaseParser
from ipaddress import IPv4Address as ip_address


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        for ip in self.ip(blob):
            ip_is_valid = self._is_valid_ip(ip)
            if ip_is_valid:
                for mp in self.mappers:
                    if 'whitelist' in dir(mp):
                        ip = self._whitelist_ip(ip, mp.whitelist)
                    if ip:
                        source = self.set_value(mp.source, ip, self.used_facts)
                        target = self.set_value(mp.target, ip, self.used_facts)
                        relationships.append(
                            Relationship(source=(mp.source, source),
                                         edge=mp.edge,
                                         target=(mp.target, target))
                        )
        return relationships

    @staticmethod
    def _is_valid_ip(raw_ip):
        try: 
            ip_address(raw_ip)
        except BaseException:
            return False
        return True

    @staticmethod
    def _whitelist_ip(raw_ip, whitelist):
        try:
            ip = ip_address(raw_ip)
        except BaseException:
            return None
        if 'multicast' not in whitelist:
            if ip.is_multicast:
                return None
        if 'loopback' not in whitelist:
            if ip.is_loopback:
                return None
        if 'link_local' not in whitelist:
            if ip.is_link_local:
                return None
        if 'reserved' not in whitelist:
            if ip.is_reserved:
                return None
        if 'global' not in whitelist:
            if ip.is_global:
                return None
        if 'unspecified' not in whitelist:
            if ip.is_unspecified:
                return None
        if 'private' not in whitelist:
            if ip.is_private:
                return None
        return str(ip)

