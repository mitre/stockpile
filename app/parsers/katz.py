from app.objects.c_relationship import Relationship
from plugins.stockpile.app.parsers.base_parser import BaseParser
from app.utility.logger import Logger

import re
from collections import defaultdict


class MimikatzBlock(object):
    def __init__(self):
        self.session = ''
        self.username = ''
        self.domain = ''
        self.logon_server = ''
        self.logon_time = ''
        self.sid = ''
        self.packages = defaultdict(list)


class Parser(BaseParser):

    def __init__(self, parser_info):
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']
        self.parse_mode = 'wdigest'
        self.log = Logger('parsing_svc')
        self.hash_check = r'([0-9a-fA-F][0-9a-fA-F] ){3}'

        self.demo = """  .#####.   mimikatz 2.1.1 (x64) #17763 Dec 31 2018 01:15:11
 .## ^ ##.  "A La Vie, A L'Amour" - (oe.eo) ** Kitten Edition **
 ## / \ ##  /*** Benjamin DELPY `gentilkiwi` ( benjamin@gentilkiwi.com )
 ## \ / ##       > http://blog.gentilkiwi.com/mimikatz
 '## v ##'       Vincent LE TOUX             ( vincent.letoux@gmail.com )
  '#####'        > http://pingcastle.com / http://mysmartlogon.com   ***/
mimikatz(powershell) # sekurlsa::logonpasswords
Authentication Id : 0 ; 41611 (00000000:0000a28b)
Session           : Interactive from 1
User Name         : DWM-1
Domain            : Window Manager
Logon Server      : (null)
Logon Time        : 1/28/2020 3:51:08 PM
SID               : S-1-5-90-1
	msv :	
	 [00000003] Primary
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * NTLM     : 86d5b0a6f0d56577e122f93c39053410
	 * SHA1     : 3e7778cd5fb5f453fc0d716027c2bec7576a3356
	tspkg :	
	wdigest :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	kerberos :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : mountainpeak.local
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	ssp :	
	credman :	
Authentication Id : 0 ; 996 (00000000:000003e4)
Session           : Service from 0
User Name         : WORK000-AMSQUAD$
Domain            : MOUNTAINPEAK
Logon Server      : (null)
Logon Time        : 1/28/2020 3:51:08 PM
SID               : S-1-5-20
	msv :	
	 [00000003] Primary
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * NTLM     : 86d5b0a6f0d56577e122f93c39053410
	 * SHA1     : 3e7778cd5fb5f453fc0d716027c2bec7576a3356
	tspkg :	
	wdigest :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	kerberos :	
	 * Username : work000-amsquad$
	 * Domain   : MOUNTAINPEAK.LOCAL
	 * Password : (null)
	ssp :	
	credman :	
Authentication Id : 0 ; 22938 (00000000:0000599a)
Session           : UndefinedLogonType from 0
User Name         : (null)
Domain            : (null)
Logon Server      : (null)
Logon Time        : 1/28/2020 3:51:08 PM
SID               : 
	msv :	
	 [00000003] Primary
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * NTLM     : 86d5b0a6f0d56577e122f93c39053410
	 * SHA1     : 3e7778cd5fb5f453fc0d716027c2bec7576a3356
	tspkg :	
	wdigest :	
	kerberos :	
	ssp :	
	credman :	
Authentication Id : 0 ; 527237 (00000000:00080b85)
Session           : RemoteInteractive from 3
User Name         : Administrator
Domain            : MOUNTAINPEAK
Logon Server      : WIN-T72NL5R98AK
Logon Time        : 1/28/2020 5:11:51 PM
SID               : S-1-5-21-2559832-618518003-1846908676-500
	msv :	
	 [00000003] Primary
	 * Username : Administrator
	 * Domain   : MOUNTAINPEAK
	 * NTLM     : e19ccf75ee54e06b06a5907af13cef42
	 * SHA1     : 9131834cf4378828626b1beccaa5dea2c46f9b63
	 [00010000] CredentialKeys
	 * NTLM     : e19ccf75ee54e06b06a5907af13cef42
	 * SHA1     : 9131834cf4378828626b1beccaa5dea2c46f9b63
	tspkg :	
	wdigest :	
	 * Username : Administrator
	 * Domain   : MOUNTAINPEAK
	 * Password : P@ssw0rd
	kerberos :	
	 * Username : Administrator
	 * Domain   : MOUNTAINPEAK.LOCAL
	 * Password : (null)
	ssp :	
	 [00000000]
	 * Username : Administrator
	 * Domain   : MOUNTAINPEAK
	 * Password : P@ssw0rd
	credman :	
Authentication Id : 0 ; 523793 (00000000:0007fe11)
Session           : Interactive from 3
User Name         : DWM-3
Domain            : Window Manager
Logon Server      : (null)
Logon Time        : 1/28/2020 5:11:51 PM
SID               : S-1-5-90-3
	msv :	
	 [00000003] Primary
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * NTLM     : 86d5b0a6f0d56577e122f93c39053410
	 * SHA1     : 3e7778cd5fb5f453fc0d716027c2bec7576a3356
	tspkg :	
	wdigest :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	kerberos :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : mountainpeak.local
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	ssp :	
	credman :	
Authentication Id : 0 ; 523674 (00000000:0007fd9a)
Session           : Interactive from 3
User Name         : DWM-3
Domain            : Window Manager
Logon Server      : (null)
Logon Time        : 1/28/2020 5:11:51 PM
SID               : S-1-5-90-3
	msv :	
	 [00000003] Primary
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * NTLM     : 86d5b0a6f0d56577e122f93c39053410
	 * SHA1     : 3e7778cd5fb5f453fc0d716027c2bec7576a3356
	tspkg :	
	wdigest :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	kerberos :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : mountainpeak.local
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	ssp :	
	credman :	
Authentication Id : 0 ; 997 (00000000:000003e5)
Session           : Service from 0
User Name         : LOCAL SERVICE
Domain            : NT AUTHORITY
Logon Server      : (null)
Logon Time        : 1/28/2020 3:51:08 PM
SID               : S-1-5-19
	msv :	
	tspkg :	
	wdigest :	
	 * Username : (null)
	 * Domain   : (null)
	 * Password : (null)
	kerberos :	
	 * Username : (null)
	 * Domain   : (null)
	 * Password : (null)
	ssp :	
	credman :	
Authentication Id : 0 ; 41540 (00000000:0000a244)
Session           : Interactive from 1
User Name         : DWM-1
Domain            : Window Manager
Logon Server      : (null)
Logon Time        : 1/28/2020 3:51:08 PM
SID               : S-1-5-90-1
	msv :	
	 [00000003] Primary
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * NTLM     : 86d5b0a6f0d56577e122f93c39053410
	 * SHA1     : 3e7778cd5fb5f453fc0d716027c2bec7576a3356
	tspkg :	
	wdigest :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	kerberos :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : mountainpeak.local
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	ssp :	
	credman :	
Authentication Id : 0 ; 999 (00000000:000003e7)
Session           : UndefinedLogonType from 0
User Name         : WORK000-AMSQUAD$
Domain            : MOUNTAINPEAK
Logon Server      : (null)
Logon Time        : 1/28/2020 3:51:08 PM
SID               : S-1-5-18
	msv :	
	tspkg :	
	wdigest :	
	 * Username : WORK000-AMSQUAD$
	 * Domain   : MOUNTAINPEAK
	 * Password : i0PI>i=sx\kLvNu< +0iCb]eb!^aY13<G[`FPz!jNK"#;nU[PbSD4W0D<OSv&$I`Zs myV=Wz<2&ioz`r4`)/ZY-WW)urJQ5E-\tp..f')Fh`)9[&ho!x%z>
	kerberos :	
	 * Username : work000-amsquad$
	 * Domain   : MOUNTAINPEAK.LOCAL
	 * Password : (null)
	ssp :	
	credman :	
	 [00000000]
	 * Username : MOUNTAINPEAK\helpdesk
	 * Domain   : dc
	 * Password : P@ssw0rd
mimikatz(powershell) # exit
Bye!"""

    def parse_katz(self, output):
        """
        Parses mimikatz output with the logonpasswords command and returns a list of dicts of the credentials.
        Args:
            output: stdout of "mimikatz.exe privilege::debug sekurlsa::logonpasswords exit"
        Returns:
            A list of MimikatzSection objects
        """
        sections = output.split('Authentication Id')  # split sections using "Authentication Id" as separator
        creds = []
        for section in sections:
            mk_section = MimikatzBlock()
            package = {}
            package_name = ''
            in_header = True
            pstate = False
            for line in section.splitlines():
                line = line.strip()
                if in_header:
                    in_header = self._parse_header(line, mk_section)
                    if in_header:
                        continue  # avoid excess parsing work
                pstate, package_name = self._process_package(line, package, package_name, mk_section)
                if pstate:
                    pstate = False
                    package = {}
            self._package_extend(package, package_name, mk_section)  # save the current ssp if necessary
            if mk_section.packages:  # save this section
                creds.append(mk_section)
        return creds

    def parse(self, blob):
        relationships = []
        try:
            parse_data = self.parse_katz(blob)
            for match in parse_data:
                if match.logon_server != '(null)':
                    if self.parse_mode in match.packages:
                        hash_pass = re.match(self.hash_check, match.packages[self.parse_mode][0]['Password'])
                        if not hash_pass:
                            for mp in self.mappers:
                                relationships.append(
                                    Relationship(source=(mp.source, match.packages[self.parse_mode][0]['Username']),
                                                 edge=mp.edge,
                                                 target=(mp.target, match.packages[self.parse_mode][0]['Password']))
                                )
        except Exception as error:
            self.log.warning('Mimikatz parser encountered an error - {}. Continuing...'.format(error))
        return relationships

    """    PRIVATE FUNCTION     """

    @staticmethod
    def _parse_header(line, mk_section):
        if line.startswith('msv'):
            return False
        session = re.match(r'^\s*Session\s*:\s*([^\r\n]*)', line)
        if session:
            mk_section.session = session.group(1)
        username = re.match(r'^\s*User Name\s*:\s*([^\r\n]*)', line)
        if username:
            mk_section.username = username.group(1)
        domain = re.match(r'^\s*Domain\s*:\s*([^\r\n]*)', line)
        if domain:
            mk_section.domain = domain.group(1)
        logon_server = re.match(r'^\s*Logon Server\s*:\s*([^\r\n]*)', line)
        if logon_server:
            mk_section.logon_server = logon_server.group(1)
        logon_time = re.match(r'^\s*Logon Time\s*:\s*([^\r\n]*)', line)
        if logon_time:
            mk_section.logon_time = logon_time.group(1)
        sid = re.match(r'^\s*SID\s*:\s*([^\r\n]*)', line)
        if sid:
            mk_section.sid = sid.group(1)
        return True

    def _process_package(self, line, package, package_name, mk_section):
        if line.startswith('['):
            self._package_extend(package, package_name, mk_section)  # this might indicate the start of a new account
            return True, package_name  # reset the package
        elif line.startswith('*'):
            m = re.match(r'\s*\* (.*?)\s*: (.*)', line)
            if m:
                package[m.group(1)] = m.group(2)
        elif line:
            match_group = re.match(r'([a-z]+) :', line)  # parse out the new section name
            if match_group:  # this is the start of a new ssp
                self._package_extend(package, package_name, mk_section)  # save the current ssp if necessary
                return True, match_group.group(1)  # reset the package
        return False, package_name

    @staticmethod
    def _package_extend(package, package_name, mk_section):
        if 'Username' in package and package['Username'] != '(null)' and \
                (('Password' in package and package['Password'] != '(null)') or 'NTLM' in package):
            mk_section.packages[package_name].append(package)
