from random import randint

from app.utility.base_obfuscator import BaseObfuscator


class Obfuscation(BaseObfuscator):

    @property
    def supported_platforms(self):
        return dict(
            darwin=['sh'],
            linux=['sh']
        )

    def __init__(self, agent):
        self.agent = agent

    """ EXECUTORS """

    def sh(self, link):
        decrypted = self.decode_bytes(link.command)
        encrypted, shift = self._apply_cipher(decrypted)
        link.pin = shift
        return 'shift=$(curl -s -X POST -H "Content-Type: application/json" '+self.agent.server+'/internals -d \'{"link":"'+link.unique+'"}\' -H "property:pin"); ' \
               'cmd=""; chr (){ [ "$1" -lt 256 ] || return 1;printf "\\$(printf \'%03o\' "$1")";};' \
               'ord (){ LC_CTYPE=C printf \'%d\' "\'$1";return $LC_CTYPE; }; ' \
               'st="'+encrypted+'"; for i in $(seq 1 ${#st}); do x=$(ord "${st:i-1:1}"); x=$((x+'+str(shift)+'));' \
               'cmd+="$(echo $(chr $x))";done;echo $cmd;'

    """ PRIVATE """

    @staticmethod
    def _apply_cipher(s, bounds=20):
        """
        Encode a command with a simple caesar cipher
        :param s: the string to encode
        :param bounds: the number of unicode code points to shift
        :return: a tuple containing the encoded command and the shift value
        """
        shift = randint(-bounds, -1)
        return ''.join([chr(ord(c) + shift) for c in s]), shift
