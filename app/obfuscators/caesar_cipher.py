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
        encrypted, shift = self.apply_cipher(decrypted)
        link.pin = shift
        return '(shift=$(curl -s -X POST -H "Content-Type: application/json" localhost:8888/internals -d \'{"link":"%s"}\' -H "property:pin");$(python -c "print(\'\'.join([chr(ord(c)+-$shift) for c in \'%s\']))");)' % (link.unique, encrypted)
