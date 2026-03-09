from random import randint

from app.utility.base_obfuscator import BaseObfuscator


class Obfuscation(BaseObfuscator):

    @property
    def supported_platforms(self):
        return dict(
            windows=['psh'],
            darwin=['sh'],
            linux=['sh']
        )

    """ EXECUTORS """

    def psh(self, link):
        decrypted = self.decode_bytes(link.command)
        encrypted, shift = self._apply_cipher(decrypted)
        return "$encrypted = '" + encrypted.replace("'","''") + "'; $cmd = ''; $encrypted = $encrypted.toCharArray(); " \
               'foreach ($letter in $encrypted) {Switch ([Byte]$letter) {' \
               '{$_ -ge 65 -and $_ -le 90} {$cmd += [char](([int][char]$letter - ' + str(65 - shift) + ') % 26 + 65)}' \
               '{$_ -ge 97 -and $_ -le 122} {$cmd += [char](([int][char]$letter - ' + str(97 - shift) + ') % 26 + 97)}' \
               'Default {$cmd += $letter}}} powershell $cmd;'

    def sh(self, link):
        decrypted = self.decode_bytes(link.command)
        encrypted, shift = self._apply_cipher(decrypted)
        return 'cmd=""; st="' + encrypted.replace('`','\\`').replace('\\','\\\\').replace('"','\\"') + \
               '"; for i in $(seq 1 ${#st}); ' \
               'do temp=$(printf %d\\\\n \\\'"$(expr substr "$st" $i 1)";); ' \
               'if [ $temp -ge 65 ] && [ $temp -le 90 ]; ' \
               'then temp=$((($temp - ' + str(65 - shift) + ') % 26 + 65)); fi; ' \
               'if [ $temp -ge 97 ] && [ $temp -le 122 ]; ' \
               'then temp=$((($temp - ' + str(97 - shift) + ') % 26 + 97)); fi; ' \
               'cmd="${cmd}$(printf \\\\$(printf \'%03o\' $temp))";done;eval $cmd;'
                

    """ PRIVATE """

    @staticmethod
    def _apply_cipher(s, bounds=26):
        """
        Encode a command with a simple caesar cipher
        :param s: the string to encode
        :param bounds: the number of unicode code points to shift
        :return: a tuple containing the encoded command and the shift value
        """
        shift = randint(1, bounds)
        return ''.join([chr((ord(c) - 65 - shift) % 26 + 65) if (65 <= ord(c) <= 90) else 
                       (chr((ord(c) - 97 - shift) % 26 + 97) if (97 <= ord(c) <= 122) else c) for c in s]), shift
