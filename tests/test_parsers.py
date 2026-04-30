"""Exhaustive tests for every parser in app/parsers/."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tests.conftest import FakeFact, FakeMapper, FakeRelationship

_REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Helper to load a parser module from disk
# ---------------------------------------------------------------------------

def _load_parser(name):
    path = _REPO_ROOT / 'app' / 'parsers' / f'{name}.py'
    spec = importlib.util.spec_from_file_location(f'parsers.{name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Parser


def _pi(source='src.trait', target='tgt.trait', edge='has', custom_parser_vals=None,
        used_facts=None, source_facts=None):
    mapper = FakeMapper(source=source, target=target, edge=edge,
                        custom_parser_vals=custom_parser_vals or {})
    return dict(mappers=[mapper], used_facts=used_facts or [],
                source_facts=source_facts or [])


# ===== basic parser =====

class TestBasicParser:
    Parser = _load_parser('basic')

    def test_single_line(self):
        p = self.Parser(_pi())
        rels = p.parse('hello')
        assert len(rels) == 1
        assert rels[0].source.value == 'hello'

    def test_multi_line(self):
        p = self.Parser(_pi())
        rels = p.parse('line1\nline2\nline3')
        assert len(rels) == 3

    def test_empty_blob(self):
        p = self.Parser(_pi())
        rels = p.parse('')
        assert rels == []

    def test_multiple_mappers(self):
        info = _pi()
        info['mappers'].append(FakeMapper(source='a', target='b', edge='e'))
        p = self.Parser(info)
        rels = p.parse('one')
        assert len(rels) == 2

    def test_whitespace_only(self):
        p = self.Parser(_pi())
        rels = p.parse('   \n   ')
        # lines with whitespace are still lines
        assert all(r.source.value.strip() == '' for r in rels)


# ===== ipaddr parser =====

class TestIpaddrParser:
    Parser = _load_parser('ipaddr')

    def test_single_valid_ip(self):
        p = self.Parser(_pi())
        rels = p.parse('Server at 192.168.1.50 is up')
        assert len(rels) == 1
        assert rels[0].source.value == '192.168.1.50'

    def test_excludes_localhost(self):
        p = self.Parser(_pi())
        rels = p.parse('127.0.0.1')
        assert len(rels) == 0

    def test_excludes_zeros(self):
        p = self.Parser(_pi())
        rels = p.parse('0.0.0.0')
        assert len(rels) == 0

    def test_excludes_broadcast(self):
        p = self.Parser(_pi())
        rels = p.parse('10.0.0.255')
        assert len(rels) == 0

    def test_excludes_subnet_zero(self):
        p = self.Parser(_pi())
        rels = p.parse('10.0.0.0')
        assert len(rels) == 0

    def test_excludes_gateway(self):
        p = self.Parser(_pi())
        rels = p.parse('10.0.0.1')
        assert len(rels) == 0

    def test_multiple_ips(self):
        p = self.Parser(_pi())
        rels = p.parse('10.10.10.50 and 10.10.10.51')
        assert len(rels) == 2

    def test_invalid_ip(self):
        p = self.Parser(_pi())
        rels = p.parse('999.999.999.999')
        assert len(rels) == 0

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []

    def test_no_ips_in_text(self):
        p = self.Parser(_pi())
        assert p.parse('no ip addresses here') == []


# ===== nmap parser =====

class TestNmapParser:
    Parser = _load_parser('nmap')

    def test_open_port(self):
        p = self.Parser(_pi())
        rels = p.parse('22/tcp open ssh')
        assert len(rels) == 1
        assert rels[0].source.value == 22

    def test_closed_port_ignored(self):
        p = self.Parser(_pi())
        rels = p.parse('22/tcp closed ssh')
        assert len(rels) == 0

    def test_multiple_ports(self):
        blob = '22/tcp open ssh\n80/tcp open http\n443/tcp closed https'
        p = self.Parser(_pi())
        rels = p.parse(blob)
        assert len(rels) == 2

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []

    def test_malformed_line(self):
        p = self.Parser(_pi())
        rels = p.parse('garbage open')
        assert len(rels) == 0


# ===== ssh parser =====

class TestSshParser:
    Parser = _load_parser('ssh')

    def test_ssh_command(self):
        p = self.Parser(_pi())
        rels = p.parse('ssh user@remote.host')
        assert len(rels) == 1
        assert rels[0].source.value == 'user@remote.host'

    def test_no_match(self):
        p = self.Parser(_pi())
        assert p.parse('scp file user@host:/tmp') == []

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []

    def test_multiple_ssh(self):
        blob = 'ssh alice@host1\nssh bob@host2'
        p = self.Parser(_pi())
        rels = p.parse(blob)
        assert len(rels) == 2


# ===== scan parser =====

class TestScanParser:
    Parser = _load_parser('scan')

    def test_colon_separated(self):
        p = self.Parser(_pi())
        rels = p.parse('host1:open')
        assert len(rels) == 1
        assert rels[0].source.value == 'host1'
        assert rels[0].target.value == 'open'

    def test_multi_line(self):
        p = self.Parser(_pi())
        rels = p.parse('a:1\nb:2')
        assert len(rels) == 2

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []


# ===== antivirus parser =====

class TestAntivirusParser:
    Parser = _load_parser('antivirus')

    def test_detects_symantec(self):
        p = self.Parser(_pi())
        rels = p.parse('Symantec Endpoint Protection')
        assert len(rels) == 1
        assert rels[0].source.value == 'symantec'

    def test_detects_norton(self):
        p = self.Parser(_pi())
        rels = p.parse('Norton Security is installed')
        assert len(rels) == 1
        assert rels[0].source.value == 'norton'

    def test_case_insensitive(self):
        p = self.Parser(_pi())
        rels = p.parse('SYMANTEC')
        assert len(rels) == 1

    def test_no_match(self):
        p = self.Parser(_pi())
        assert p.parse('Windows Defender') == []

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []

    def test_both_detected(self):
        p = self.Parser(_pi())
        rels = p.parse('symantec\nnorton')
        assert len(rels) == 2


# ===== filename parser =====

class TestFilenameParser:
    Parser = _load_parser('filename')

    def test_simple_filename(self):
        p = self.Parser(_pi())
        rels = p.parse('important_doc.pdf')
        assert len(rels) >= 1

    def test_no_filename(self):
        p = self.Parser(_pi())
        assert p.parse('') == []

    def test_multiple_filenames(self):
        p = self.Parser(_pi())
        rels = p.parse('file1.txt\nfile2.docx')
        assert len(rels) >= 2


# ===== broadcastip parser =====

class TestBroadcastipParser:
    Parser = _load_parser('broadcastip')

    def test_broadcast_keyword(self):
        p = self.Parser(_pi())
        rels = p.parse('broadcast 10.0.0.255')
        assert len(rels) == 1
        assert rels[0].source.value == '10.0.0.255'

    def test_bcast_format(self):
        p = self.Parser(_pi())
        rels = p.parse('Bcast:192.168.1.255')
        assert len(rels) == 1

    def test_no_broadcast(self):
        p = self.Parser(_pi())
        assert p.parse('some text') == []

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []


# ===== firewallping parser =====

class TestFirewallpingParser:
    Parser = _load_parser('firewallping')

    def test_zero_percent_loss(self):
        p = self.Parser(_pi())
        blob = '    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)'
        rels = p.parse(blob)
        assert len(rels) == 1

    def test_nonzero_loss_ignored(self):
        p = self.Parser(_pi())
        blob = '    Packets: Sent = 4, Received = 2, Lost = 2 (50% loss)'
        rels = p.parse(blob)
        assert len(rels) == 0

    def test_no_packets_line(self):
        p = self.Parser(_pi())
        assert p.parse('some random output') == []

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []


# ===== 54ndc47_remote_copy parser =====

class TestRemoteCopyParser:
    Parser = _load_parser('54ndc47_remote_copy')

    def test_success_flag(self):
        fact = FakeFact(trait='src.trait', value='10.10.10.5')
        info = _pi(used_facts=[fact])
        p = self.Parser(info)
        blob = 'VERBOSE: Performing the operation "Copy File" on target "C:\\temp".'
        rels = p.parse(blob)
        assert len(rels) == 1
        assert rels[0].source.value == '10.10.10.5'

    def test_no_success_flag(self):
        p = self.Parser(_pi())
        assert p.parse('some other output') == []

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []

    def test_returns_after_first_match(self):
        fact = FakeFact(trait='src.trait', value='10.10.10.5')
        info = _pi(used_facts=[fact])
        p = self.Parser(info)
        blob = ('VERBOSE: Performing the operation "Copy File" on target "C:\\a".\n'
                'VERBOSE: Performing the operation "Copy File" on target "C:\\b".')
        rels = p.parse(blob)
        assert len(rels) == 1


# ===== acrn parser =====

class TestAcrnParser:
    Parser = _load_parser('acrn')

    def test_parses_vm_names(self):
        p = self.Parser(_pi())
        blob = 'vm1\t\trunning\nvm2\t\tstopped'
        rels = p.parse(blob)
        assert len(rels) == 2
        assert rels[0].source.value == 'vm1'

    def test_single_vm(self):
        p = self.Parser(_pi())
        rels = p.parse('myvm\t\trunning')
        assert len(rels) == 1

    def test_empty_produces_one_empty(self):
        p = self.Parser(_pi())
        rels = p.parse('')
        # split on '\n' always gives at least ['']
        assert len(rels) == 1


# ===== nbtstat parser =====

class TestNbtstatParser:
    Parser = _load_parser('nbtstat')

    def test_group_match(self):
        info = _pi()
        p = self.Parser(info)
        blob = '    WORKGROUP       <00>  GROUP'
        rels = p.parse(blob)
        assert len(rels) == 1
        assert rels[0].source.value == 'WORKGROUP'

    def test_no_group_match(self):
        p = self.Parser(_pi())
        blob = '    HOSTNAME        <00>  UNIQUE'
        rels = p.parse(blob)
        assert len(rels) == 0

    def test_empty_blob(self):
        p = self.Parser(_pi())
        rels = p.parse('')
        assert rels == []

    def test_none_blob(self):
        p = self.Parser(_pi())
        rels = p.parse(None)
        assert rels == []


# ===== net_view parser =====

class TestNetViewParser:
    Parser = _load_parser('net_view')

    def test_disk_share(self):
        fact = FakeFact(trait='src.trait', value='server.domain.local')
        info = _pi(used_facts=[fact], source_facts=[])
        info['source_facts'] = []
        p = self.Parser(info)
        p.source_facts = []
        blob = 'Share1      Disk     My share'
        rels = p.parse(blob)
        assert len(rels) == 1
        assert rels[0].target.value == 'Share1'

    def test_ipc_share(self):
        fact = FakeFact(trait='src.trait', value='server.domain.local')
        info = _pi(used_facts=[fact])
        info['source_facts'] = []
        p = self.Parser(info)
        p.source_facts = []
        blob = 'IPC$       IPC      Remote IPC'
        rels = p.parse(blob)
        assert len(rels) == 1

    def test_no_shares(self):
        fact = FakeFact(trait='src.trait', value='server')
        info = _pi(used_facts=[fact])
        info['source_facts'] = []
        p = self.Parser(info)
        p.source_facts = []
        blob = 'No entries found'
        rels = p.parse(blob)
        assert rels == []


# ===== share_mounted parser =====

class TestShareMountedParser:
    Parser = _load_parser('share_mounted')

    def test_success_message(self):
        fact = FakeFact(trait='src.trait', value='remote-host')
        info = _pi(used_facts=[fact])
        p = self.Parser(info)
        blob = 'The command completed successfully.'
        rels = p.parse(blob)
        assert len(rels) == 1
        assert rels[0].source.value == 'remote-host'

    def test_no_success(self):
        p = self.Parser(_pi())
        assert p.parse('command failed') == []

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []


# ===== printer_queue parser =====

class TestPrinterQueueParser:
    Parser = _load_parser('printer_queue')

    def test_queued_doc(self):
        p = self.Parser(_pi())
        blob = '1  owner  HP LaserJet  My Document.docx  500 bytes'
        rels = p.parse(blob)
        assert len(rels) == 1

    def test_heading_ignored(self):
        p = self.Parser(_pi())
        blob = 'Doc# Owner Printer Name Size\n1  owner  HP  report.pdf  1 MB'
        rels = p.parse(blob)
        assert len(rels) == 1

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []


# ===== wifipref parser =====

class TestWifiprefParser:
    Parser = _load_parser('wifipref')

    def test_all_user_profile(self):
        p = self.Parser(_pi())
        blob = 'All User Profile     : HomeNetwork\nAll User Profile     : WorkNetwork'
        rels = p.parse(blob)
        assert len(rels) == 2
        assert rels[0].source.value == 'HomeNetwork'

    def test_plain_list(self):
        p = self.Parser(_pi())
        blob = 'Profiles:\nNetwork1\nNetwork2'
        rels = p.parse(blob)
        assert len(rels) == 2
        values = [r.source.value for r in rels]
        assert 'Network1' in values
        assert 'Network2' in values

    def test_empty(self):
        p = self.Parser(_pi())
        assert p.parse('') == []


# ===== reverse_nslookup parser =====

class TestReverseNslookupParser:
    Parser = _load_parser('reverse_nslookup')

    def test_valid_nslookup(self):
        info = _pi()
        p = self.Parser(info)
        blob = 'Server: dns.local\nAddress: 10.0.0.1\n\nName:\thost.domain.local\nAddress:\t192.168.1.10'
        rels = p.parse(blob)
        assert len(rels) == 1
        assert rels[0].source.value == 'host.domain.local'
        assert rels[0].target.value == '192.168.1.10'

    def test_non_existent_domain_returns_empty(self):
        info = _pi()
        p = self.Parser(info)
        blob = 'Non-existent domain'
        result = p.nslookup_parser(blob)
        assert result is None

    def test_empty_returns_none(self):
        info = _pi()
        p = self.Parser(info)
        result = p.nslookup_parser('')
        assert result is None


# ===== json parser =====

class TestJsonParser:
    Parser = _load_parser('json')

    def test_simple_json(self):
        info = _pi(custom_parser_vals={'json_key': 'name'})
        p = self.Parser(info)
        blob = json.dumps({'name': 'test_value'})
        rels = p.parse(blob)
        assert len(rels) == 1
        assert rels[0].source.value == 'test_value'

    def test_nested_json(self):
        info = _pi(custom_parser_vals={'json_key': 'ip'})
        p = self.Parser(info)
        blob = json.dumps({'outer': {'ip': '10.10.10.10'}})
        rels = p.parse(blob)
        assert len(rels) == 1
        assert rels[0].source.value == '10.10.10.10'

    def test_json_list(self):
        info = _pi(custom_parser_vals={'json_key': 'host'})
        p = self.Parser(info)
        blob = json.dumps([{'host': 'a'}, {'host': 'b'}])
        rels = p.parse(blob)
        assert len(rels) == 2

    def test_json_type_filter(self):
        info = _pi(custom_parser_vals={'json_key': 'val', 'json_type': 'str'})
        p = self.Parser(info)
        blob = json.dumps({'val': 'hello', 'nested': {'val': 123}})
        rels = p.parse(blob)
        assert len(rels) == 1
        assert rels[0].source.value == 'hello'

    def test_invalid_json(self):
        info = _pi(custom_parser_vals={'json_key': 'x'})
        p = self.Parser(info)
        rels = p.parse('not json')
        assert rels == []

    def test_missing_json_key_config(self):
        info = _pi(custom_parser_vals={})
        p = self.Parser(info)
        blob = json.dumps({'a': 1})
        rels = p.parse(blob)
        assert rels == []

    def test_dict_value_serialized(self):
        info = _pi(custom_parser_vals={'json_key': 'data', 'json_type': 'dict'})
        p = self.Parser(info)
        blob = json.dumps({'data': {'nested': True}})
        rels = p.parse(blob)
        assert len(rels) == 1
        # dict values get json.dumps serialized
        assert 'nested' in rels[0].source.value


# ===== bookmarks parser =====

class TestBookmarksParser:
    Parser = _load_parser('bookmarks')

    def _bookmark_json(self):
        return json.dumps({
            'roots': {
                'bookmark_bar': {
                    'children': [
                        {'name': 'Site1', 'url': 'https://example.com'},
                        {'name': 'Folder', 'children': [
                            {'name': 'Site2', 'url': 'https://test.com',
                             'meta_info': {'last_visited_desktop': '100'}},
                        ]},
                    ]
                }
            }
        })

    def test_parses_bookmarks(self):
        p = self.Parser(_pi())
        rels = p.parse(self._bookmark_json())
        assert len(rels) == 2
        urls = [r.target.value for r in rels]
        assert 'https://example.com' in urls
        assert 'https://test.com' in urls

    def test_invalid_json(self):
        p = self.Parser(_pi())
        rels = p.parse('not json')
        assert rels == []

    def test_empty_children(self):
        blob = json.dumps({'roots': {'bookmark_bar': {'children': []}}})
        p = self.Parser(_pi())
        rels = p.parse(blob)
        assert rels == []

    def test_meta_info_score(self):
        p = self.Parser(_pi())
        rels = p.parse(self._bookmark_json())
        scored = [r for r in rels if r.score > 1]
        assert len(scored) >= 1


# ===== gdomain parser =====

class TestGdomainParser:
    Parser = _load_parser('gdomain')

    def test_parses_hostname_and_version(self):
        info = _pi()
        p = self.Parser(info)
        blob = ('dnshostname                      : dc01.example.com\n'
                'operatingsystemversion           : 10.0 (14393)\n')
        rels = p.parse(blob)
        assert len(rels) == 1
        assert rels[0].source.value == 'dc01.example.com'

    def test_empty_blob(self):
        info = _pi()
        p = self.Parser(info)
        rels = p.parse('')
        assert rels == []

    def test_missing_version(self):
        info = _pi()
        p = self.Parser(info)
        blob = 'dnshostname : server.local\n'
        rels = p.parse(blob)
        assert rels == []

    def test_domain_error(self):
        info = _pi()
        p = self.Parser(info)
        blob = "Exception (0x80005000): Can't contact LDAP"
        rels = p.parse(blob)
        assert rels == []

    def test_crlf_blocks(self):
        info = _pi()
        p = self.Parser(info)
        blob = ('dnshostname                      : dc01.example.com\r\n'
                'operatingsystemversion           : 10.0 (14393)\r\n')
        rels = p.parse(blob)
        assert len(rels) == 1


# ===== static parser =====

class TestStaticParser:
    Parser = _load_parser('static')

    def test_static_source_only(self):
        info = _pi(custom_parser_vals={'source': 'my_value'})
        p = self.Parser(info)
        rels = p.parse('anything')
        assert len(rels) == 1
        assert rels[0].source.value == 'my_value'
        # target defaults to source
        assert rels[0].target.value == 'my_value'

    def test_static_source_and_target(self):
        info = _pi(custom_parser_vals={'source': 'src_val', 'target': 'tgt_val'})
        p = self.Parser(info)
        rels = p.parse('anything')
        assert len(rels) == 1
        assert rels[0].source.value == 'src_val'
        assert rels[0].target.value == 'tgt_val'

    def test_no_source(self):
        info = _pi(custom_parser_vals={})
        p = self.Parser(info)
        rels = p.parse('anything')
        assert rels == []

    def test_ignores_blob_content(self):
        info = _pi(custom_parser_vals={'source': 'static_fact'})
        p = self.Parser(info)
        r1 = p.parse('foo')
        r2 = p.parse('bar')
        assert r1[0].source.value == r2[0].source.value


# ===== katz parser =====

class TestKatzParser:
    Parser = _load_parser('katz')

    MIMIKATZ_OUTPUT = """Authentication Id : 0 ; 123456 (00000000:0001e240)
         Session           : Interactive from 1
         User Name         : administrator
         Domain            : TESTDOMAIN
         Logon Server      : DC01
         Logon Time        : 1/1/2023 12:00:00 AM
         SID               : S-1-5-21-1234-5678

         msv :
          [00000003] Primary
          * Username : administrator
          * Domain   : TESTDOMAIN
          * NTLM     : aabbccdd11223344
          * SHA1     : 1122334455667788

         wdigest :
          * Username : administrator
          * Domain   : TESTDOMAIN
          * Password : P@ssw0rd

         kerberos :
          * Username : administrator
          * Domain   : TESTDOMAIN.LOCAL
          * Password : P@ssw0rd

"""

    def test_parse_katz_sessions(self):
        info = _pi(source='domain.user.name', target='domain.user.password')
        p = self.Parser(info)
        sessions = p.parse_katz(self.MIMIKATZ_OUTPUT)
        assert len(sessions) > 0
        assert sessions[0].username == 'administrator'
        assert sessions[0].domain == 'TESTDOMAIN'

    def test_parse_returns_relationships(self):
        info = _pi(source='domain.user.name', target='domain.user.password')
        p = self.Parser(info)
        rels = p.parse(self.MIMIKATZ_OUTPUT)
        assert len(rels) > 0

    def test_empty_output(self):
        info = _pi(source='domain.user.name', target='domain.user.password')
        p = self.Parser(info)
        rels = p.parse('')
        assert rels == []

    def test_null_logon_server_skipped(self):
        blob = """Authentication Id : 0 ; 999
         Session           : Unknown
         User Name         : DWM-1
         Domain            : Window Manager
         Logon Server      : (null)
         Logon Time        : 1/1/2023

         msv :
          [00000003] Primary
          * Username : DWM-1
          * Domain   : Window Manager
          * NTLM     : aabbccdd
"""
        info = _pi(source='domain.user.name', target='domain.user.password')
        p = self.Parser(info)
        rels = p.parse(blob)
        assert rels == []

    def test_credman_provider(self):
        blob = """Authentication Id : 0 ; 100
         Session           : Interactive from 1
         User Name         : testuser
         Domain            : CORP
         Logon Server      : (null)
         Logon Time        : 1/1/2023

         msv :

         credman :
          [00000000]
          * Username : admin@service.com
          * Domain   : service.com
          * Password : SecretPass
"""
        info = _pi(source='domain.user.name', target='domain.user.password')
        p = self.Parser(info)
        rels = p.parse(blob)
        assert len(rels) > 0

    def test_hash_check_filters(self):
        """Hash-looking passwords should be skipped."""
        blob = """Authentication Id : 0 ; 100
         Session           : Interactive from 1
         User Name         : testuser
         Domain            : CORP
         Logon Server      : DC01
         Logon Time        : 1/1/2023

         msv :

         wdigest :
          * Username : testuser
          * Domain   : CORP
          * Password : aa bb cc dd ee ff
"""
        info = _pi(source='domain.user.name', target='domain.user.password')
        p = self.Parser(info)
        rels = p.parse(blob)
        assert rels == []


# ===== netlocalgroup parser =====

class TestNetlocalgroupParser:
    Parser = _load_parser('netlocalgroup')

    def test_extract_domain_user(self):
        info = _pi()
        p = self.Parser(info)
        # The parser splits on \r\n\r\n and expects each block to have k:v lines
        # ComputerName block comes first, then user blocks, then WARNING marks end
        blob = (
            'ComputerName : HOST1\r\n'
            'MemberName   : CORP\\admin\r\n'
            'SID          : S-1-5-21-123\r\n'
            'IsDomain     : True\r\n'
            'IsGroup      : False\r\n'
            '\r\n'
            'WARNING: done\r\n'
        )
        users = p.extract(blob)
        assert len(users) == 1
        assert users[0]['username'] == 'admin'
        assert users[0]['windows_domain'] == 'corp'

    def test_extract_local_user(self):
        info = _pi()
        p = self.Parser(info)
        blob = (
            'ComputerName : HOST1\r\n'
            'MemberName   : HOST1\\localadmin\r\n'
            'SID          : S-1-5-21-456\r\n'
            'IsDomain     : False\r\n'
            'IsGroup      : False\r\n'
            '\r\n'
            'WARNING: done\r\n'
        )
        users = p.extract(blob)
        assert len(users) == 1
        assert users[0]['hostname'] == 'host1'

    def test_parse_with_domain_user(self):
        fact = FakeFact(trait='src.trait', value='HOST1')
        info = _pi(used_facts=[fact])
        p = self.Parser(info)
        blob = (
            'ComputerName : HOST1\r\n'
            'MemberName   : CORP\\admin\r\n'
            'SID          : S-1-5-21-123\r\n'
            'IsDomain     : True\r\n'
            'IsGroup      : False\r\n'
            '\r\n'
            'WARNING: done\r\n'
        )
        rels = p.parse(blob)
        has_backup = any(r.source.trait == 'backup.admin.ability' for r in rels)
        assert not has_backup

    def test_parse_fallback_when_no_domain_users(self):
        fact = FakeFact(trait='src.trait', value='HOST1')
        info = _pi(used_facts=[fact])
        p = self.Parser(info)
        blob = (
            'ComputerName : HOST1\r\n'
            'MemberName   : HOST1\\Administrators\r\n'
            'SID          : S-1-5-32-544\r\n'
            'IsDomain     : False\r\n'
            'IsGroup      : True\r\n'
            '\r\n'
            'WARNING: done\r\n'
        )
        rels = p.parse(blob)
        assert any(r.source.trait == 'backup.admin.ability' for r in rels)

    def test_empty_extract(self):
        info = _pi()
        p = self.Parser(info)
        blob = 'ComputerName : HOST\r\n\r\nWARNING: done'
        users = p.extract(blob)
        # When no parseable data, extract returns None or empty list
        assert not users
