import random

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

    def recieve_beacon(self):
        """ """
        pass

    def handle_beacon(self):
        g = Github(self.key)
        for gist in g.get_user().get_gists():
            if 'beacon' == gist.description:
                for file in gist.files:
                    print(gist.files[file].content)
                    #data = json.loads(gist.files[file].content)
