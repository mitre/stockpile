from base64 import b64encode

from app.utility.base_obfuscator import BaseObfuscator


class Obfuscation(BaseObfuscator):

    @property
    def supported_platforms(self):
        return dict(
            windows=['psh'],
            darwin=['sh'],
            linux=['sh']
        )

    def __init__(self, agent):
        self.agent = agent

    def run(self, link, **kwargs):
        link.command = link.command.replace('=', '')
        return super().run(link)

    def sh(self, link, **kwargs):
        return 'eval "$(echo %s | base64 --decode)"' % str(self._add_padding(link.command).encode(), 'utf-8')

    def psh(self, link, **kwargs):
        recoded = b64encode(self.decode_bytes(self._add_padding(link.command)).encode('UTF-16LE'))
        return 'powershell -Enc %s' % recoded.decode('utf-8')

    """ PRIVATE """

    def _add_padding(self, s):
        while not self.is_base64(s):
            s = s + '='
        return s
    
