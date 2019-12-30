import random
import string

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
        cmd, extra = self._jumble_command(link.command)
        link.command = cmd
        return super().run(link, extra=extra)

    @staticmethod
    def sh(link, **kwargs):
        extra_chars = kwargs.get('extra') + 1
        return 'eval "$(echo %s | rev | cut -c%s- | rev | base64 --decode)"' % (str(link.command.encode(), 'utf-8'), extra_chars)

    def psh(self, link, **kwargs):
        extra_chars = kwargs.get('extra') + 1
        recoded = b64encode(self.decode_bytes(link.command).encode('UTF-16LE'))
        return 'powershell -Enc %s.Substring(0,%s)' % (recoded.decode('utf-8'), len(link.command)-extra_chars)

    """ PRIVATE """

    def _jumble_command(self, s):
        extra = 0
        while self.is_base64(s):
            s = s + self._random_char()
            extra += 1
        return s, extra

    @staticmethod
    def _random_char():
        return random.choice(string.ascii_letters + string.digits)
