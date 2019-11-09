import random
import json

from base64 import b64encode, b64decode
from app.objects.c_c2 import C2
from github import Github


class Gist(C2):

    def __init__(self, module_info):
        index = random.randint(0, len(module_info['config']['keys'])-1)
        self.key = module_info['config']['keys'][index]
        self.c2_type = module_info['c2_type']

    def encode_config_info(self):
        """ Returns one of the API keys to be encoded into the agent """
        return self.key

    def get_beacons(self):
        g = Github(self.key)
        beacons = []
        for gist in g.get_user().get_gists():
            if 'beacon' == gist.description:
                for file in gist.files:
                    beacon = self._decode_bytes(gist.files[file].content)
                    beacons.append(json.loads(beacon))
        return beacons

    """ PRIVATE """

    @staticmethod
    def _decode_bytes(s):
        return b64decode(s).decode('utf-8', errors='ignore').replace('\n', '')