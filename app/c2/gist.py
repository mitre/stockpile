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

    async def get_results(self):
        """ Retrieve all GIST posted results for a particular api key"""
        result_urls = await self._get_raw_gist_urls(comm_type='results')
        return await self._get_gist_content(result_urls)

    async def get_beacons(self):
        """ Retrieve all GIST beacons for a particular api key"""
        beacon_urls = await self._get_raw_gist_urls(comm_type='beacon')
        return await self._get_gist_content(beacon_urls)

    async def post_instructions(self, text, paw):
        """ Post an instruction for the agent to execute as an encoded GIST """
        if len(json.loads(self.decode_bytes(text))['instructions']) < 1:
            return
        if await self._paw_has_instructions(paw):
            return
        headers = {'Authorization': 'token {}'.format(self.key)}
        gist = {
            "description": "instructions-{}".format(paw),
            "public": False,
            "files": {
                str(uuid.uuid4()): {
                    "content": text
                }
            }
        }
        async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            return await self._post(session, 'https://api.github.com/gists', body=gist)

    """ PRIVATE """

    async def _get_gist_content(self, urls):
        all_content = []
        for url in urls:
            headers = {'Authorization': 'token {}'.format(self.key)}
            async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                content = json.loads(self.decode_bytes(await self._fetch(session, url)))
                all_content.append(content)
        return all_content

    async def _get_raw_gist_urls(self, comm_type):
        raw_urls = []
        for gist in await self._get_gists():
            if comm_type in gist['description']:
                for file in gist.get('files'):
                    raw_url = gist['files'][file]['raw_url']
                    raw_urls.append(raw_url)
        return raw_urls

    async def _get_gists(self):
        headers = {'Authorization': 'token {}'.format(self.key)}
        async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            return json.loads(await self._fetch(session, 'https://api.github.com/gists'))

    @staticmethod
    async def _fetch(session, url):
        async with session.get(url) as response:
            return await response.text()

    @staticmethod
    async def _post(session, url, body):
        async with session.post(url, json=body) as response:
            return await response.text()

    async def _paw_has_instructions(self, paw):
        for gist in await self._get_gists():
            if 'instructions-{}'.format(paw) == gist['description']:
                return True
        return False
