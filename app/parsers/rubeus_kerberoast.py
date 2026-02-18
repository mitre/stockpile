import re
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser

class Parser(BaseParser):

    relationship_sources = []

    def parse(self, blob):
        """Parse the output from `.\Rubeus.exe kerberoast /simple`
 
        Like:
               ______        _
              (_____ \      | |
               _____) )_   _| |__  _____ _   _  ___
              |  __  /| | | |  _ \| ___ | | | |/___)
              | |  \ \| |_| | |_) ) ____| |_| |___ |
              |_|   |_|____/|____/|_____)____/(___/
 
              v1.5.0
 
 
            [*] Action: Kerberoasting
 
            [*] NOTICE: AES hashes will be returned for AES-enabled accounts.
            [*]         Use /ticket:X or /tgtdeleg to force RC4_HMAC for these accounts.
 
            [*] Searching the current domain for Kerberoastable users
 
            [*] Total kerberoastable users : 1
 
            $krb5tgs$23$*svc-sql$acme.org$MSSQL/sql1.acme.org:1443*$77A12FE66A1[...truncated...]
        """
        relationships = []
        username = None
        tgs_hash = None

        lines = blob.replace('\r\n', '\n').split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Extract username
            if line.startswith('[*] SamAccountName'):
                # e.g. [*] SamAccountName         : jli
                username = line.split(':', 1)[-1].strip()
            # Extract hash (may be multi-line)
            elif line.startswith('[*] Hash'):
                # The hash starts after the colon
                hash_line = line.split(':', 1)[-1].strip()
                tgs_hash_lines = [hash_line] if hash_line else []
                # Collect subsequent indented lines as part of the hash
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    # Stop if the next line is not indented or is empty
                    if not next_line.startswith(' ') and not next_line.startswith('\t'):
                        break
                    tgs_hash_lines.append(next_line.strip())
                    j += 1
                tgs_hash = ''.join(tgs_hash_lines)
                i = j - 1  # Move i to last hash line
            i += 1

        # Validate extraction
        if username and tgs_hash and tgs_hash.startswith('$krb5tgs$'):
            relationships.extend(self.create_relationships(username, tgs_hash))

        return relationships

    def create_relationships(self, source_value, target_value):
        relationships = []
        for mp in self.mappers:
            source_fact_search = [fact for fact in self.relationship_sources
                                  if fact.trait == mp.source and fact.value == source_value]
            if source_fact_search:
                source_fact = source_fact_search[0]
            else:
                source_fact = Fact(mp.source, source_value)
                self.relationship_sources.append(source_fact)
            relationships.append(
                Relationship(source=source_fact,
                             edge=mp.edge,
                             target=Fact(mp.target, target_value))
            )
        return relationships
