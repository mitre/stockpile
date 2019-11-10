import random
import json
import uuid
import pprint
import aiohttp

from app.objects.c_c2 import C2


class Gist(C2):

    def __init__(self, module_info):
        index = random.randint(0, len(module_info['config']['keys'])-1)
        self.key = module_info['config']['keys'][index]
        self.c2_type = module_info['c2_type']

    def encode_config_info(self):
        """ Returns one of the API keys to be encoded into the agent """
        return self.key

    async def get_beacons(self):
        """ Retrieve all GitHub gist communication for a particular api key"""
        headers = {'Authorization': 'token {}'.format(self.key)}
        beacons, beacon_urls = [], []
        async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            gists = json.loads(await self._fetch(session, 'https://api.github.com/gists'))
            for gist in gists:
                if 'beacon' in gist['description']:
                    for file in gist.get('files'):
                        raw_url = gist['files'][file]['raw_url']
                        beacon_urls.append(raw_url)

        for url in beacon_urls:
            async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                beacon = json.loads(self.decode_bytes(await self._fetch(session, url)))
                beacons.append(beacon)

        return beacons





    async def post_instructions(self, instructions, paw):
        """ Post an instruction for the agent to execute as an encoded GIST """
        
        return None


    """ PRIVATE """

    @staticmethod
    async def _fetch(session, url):
        async with session.get(url) as response:
            return await response.text()

