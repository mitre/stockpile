import glob
import os
import re

from app.utility.base_planning_svc import BasePlanningService

valid_vars = dict(application=['name', 'port', 'is_vulnerable', 'user', 'type'],
                  custom=['bookmark_title', 'bookmark_url', 'bookmark_path', 'organization_name',
                          'organization_domain', 'organization_email', 'organization_email_host', 'wifi_ssid',
                          'wifi_password', 'wifi_channel', 'wifi_frequency', 'vulnerability_name', 'vulnerability_cve',
                          'vulnerability_ip', 'vulnerability_port', 'vulnerability_process', 'numgroom',
                          'vulnerable_path', 'text_keystrokes', 'text_command', 'protocol_name', 'contact_html',
                          'git_dir', 'dropbox_api_key', 'dropbox_target_dir', 'github_username', 'github_repository',
                          'github_token', 'github_branch', 'github_url', 'archive_password', 'file_size_chunk',
                          'ftp_username', 'ftp_password', 'ftp_server', 's3_region', 's3_name', 's3_bucket', 's3_id',
                          's3_path', 's3_group', 's3_policy', 'psexec_path', 'host_interface', 'netrange', 'https',
                          'rdp_id', 'agent_args', 'rdp_hosts', 'rdp_users', 'rdp_passwords'],
                  cronjob=['path', 'time', 'is_new', 'type'],
                  file=['name', 'path', 'dir', 'permissions', 'owner', 'modified', 'accessed', 'created', 'extension',
                        'size', 'version', 'hash', 'is_malicious', 'type', 'backup', 'is_screenshot', 'is_sensitive'
                                                                                                      'is_compressed',
                        'encryption_key', 'staged_at'],
                  hash=['type', 'digest', 'is_malicious'],
                  host=['application', 'current_time', 'directory', 'port', 'ip', 'hostname', 'filepath', 'cronjob',
                        'schtask', 'service', 'fqdn', 'url', 'ssh_cmd', 'os', 'domain', 'share', 'group', 'mac',
                        'type', 'model', 'socket', 'user', 'unc_path'],
                  ip=['address', 'is_suspicious', 'version', 'class'],
                  network=['name', 'ad', 'file', 'directory', 'range', 'broadcast_ip'],
                  os=['name', 'family', 'version'],
                  port=['number', 'name', 'is_unauthorized'],
                  process=['name', 'id', 'guid', 'parent', 'is_unauthorized', 'port', 'command_line', 'file',
                           'integrity_level', 'is_sysmon', 'sysmon', 'is_hidden'],
                  resource=['name', 'user', 'location'],
                  schtask=['name', 'user', 'target'],
                  service=['name', 'is_modifiable', 'modifiable', 'status'],
                  user=['name.local', 'name.domain', 'system_path', 'password', 'upn', 'tgt', 'guid', 'logon_type',
                        'sid', 'privilege_level', 'ntlm_hash', 'sha1_hash', 'domain', 'group'],
                  url=['path', 'suspicious', 'category', 'extension', 'port'],
                  sysmon=['guid', 'child_id', 'grandchild_id', 'event_id', 'record_id']
                  )

reserved = ['payload', 'exe_name', 'original_link_id', 'server', 'group', 'paw']


class TestStockpile:
    LIBRARY_GLOB_PATH = os.path.join(__file__, "..", '..', "data", "abilities")
    SOURCE_GLOB_PATH = os.path.join(__file__, "..", "..", "data", "sources")
    re_variable = BasePlanningService().re_variable
    re_trait = re.compile(r'trait: .[^#\n ]*', flags=re.DOTALL)
    re_source = re.compile(r'source: .[^#\n ]*', flags=re.DOTALL)
    re_target = re.compile(r'target: .[^#\n ]*', flags=re.DOTALL)

    def test_ability_coverage(self):
        list_of_bad_files = dict()
        for filename in glob.iglob(os.path.join(self.LIBRARY_GLOB_PATH, '**', '*.yml'), recursive=True):
            with open(filename, 'r') as fio:
                data = fio.read()
                bad_vars = self._parse_file(data)
                if bad_vars:
                    list_of_bad_files[os.path.sep.join(filename.split(os.path.sep)[-2:])] = bad_vars
        assert list_of_bad_files == dict()

    def test_source_coverage(self):
        list_of_bad_files = dict()
        for filename in glob.iglob(os.path.join(self.SOURCE_GLOB_PATH, '**', '*.yml'), recursive=True):
            with open(filename, 'r') as fio:
                data = fio.read()
                bad_vars = self._parse_file(data)
                if bad_vars:
                    list_of_bad_files[os.path.sep.join(filename.split(os.path.sep)[-1:])] = bad_vars
        assert list_of_bad_files == dict()

    def _parse_file(self, file_contents):
        bad_vars = set()
        variables_and_globals = set(x for x in re.findall(self.re_variable, file_contents))
        [variables_and_globals.add(x[7:]) for x in re.findall(self.re_trait, file_contents)]
        [variables_and_globals.add(x[8:]) for x in re.findall(self.re_source, file_contents)]
        [variables_and_globals.add(x[8:]) for x in re.findall(self.re_target, file_contents)]
        for vg in variables_and_globals:
            breakdown = vg.split('.')
            if len(breakdown) == 3:  # subtype fact (user.name.domain, etc.)
                breakdown = [breakdown[0], '.'.join(breakdown[1:])]
            if len(breakdown) == 1:
                if breakdown[0] not in reserved:
                    bad_vars.add(vg)
            elif len(breakdown) == 2:
                if breakdown[0] in valid_vars:
                    if breakdown[1] in valid_vars[breakdown[0]]:
                        continue
                bad_vars.add(vg)
            else:
                bad_vars.add(vg)
        return bad_vars
