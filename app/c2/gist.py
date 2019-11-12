import random
import json
import uuid
import aiohttp
from base64 import b64encode, b64decode

from app.objects.c_c2 import C2


class Gist(C2):

    def __init__(self, module_info):
        self.key = module_info['config']['key']
        self.c2_type = module_info['c2_type']

    def encode_config_info(self):
        """
        Returns one of the GIST API keys to be encoded into the agent
        :return: GIST api key
        """
        return self.key

    async def get_results(self):
        """
        Retrieve all GIST posted results for a particular api key
        :return:
        """
        results = await self._get_raw_gist_urls(comm_type='results')
        result_content = await self._get_gist_content([result[0] for result in results])
        await self._delete_gists([result[1] for result in results])
        return result_content

    async def get_beacons(self):
        """ Retrieve all GIST beacons for a particular api key"""
        beacons = await self._get_raw_gist_urls(comm_type='beacon')
        beacon_content = await self._get_gist_content([beacon[0] for beacon in beacons])
        await self._delete_gists([beacon[1] for beacon in beacons])
        return beacon_content

    async def post_payloads(self, payloads, paw):
        """
        Given a list of payloads and an agent paw, posts the payloads as a series of base64 encoded
        files attached to a single gist
        :param payloads:
        :param paw:
        :return:
        """

        files = {payload[0]: dict(content=self.encode_string(payload[1])) for payload in payloads}
        if len(files) < 1 or await self._wait_for_paw(paw, comm_type='payloads'):
            return
        gist = self._build_gist_content(comm_type='payloads', paw=paw, files=files)
        return await self._post_gist(gist)

    async def post_instructions(self, text, paw):
        """
        Post an instruction for the agent to execute as an encoded GIST
        :param text: The instruction text for the agent to execute
        :param paw: The paw for the agent to execute
        :return:
        """
        if len(json.loads(self.decode_bytes(text))['instructions']) < 1 or \
                await self._wait_for_paw(paw, comm_type='instructions'):
            return
        gist = self._build_gist_content(comm_type='instructions', paw=paw, files={str(uuid.uuid4()): {"content": text}})
        return await self._post_gist(gist)

    """ PRIVATE """

    async def _post_gist(self, gist):
        headers = {'Authorization': 'token {}'.format(self.key)}
        async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            return await self._post(session, 'https://api.github.com/gists', body=gist)

    @staticmethod
    def _build_gist_content(comm_type, paw, files):
        return {
            "description": "{}-{}".format(comm_type, paw),
            "public": False,
            "files": files}

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
                    raw_urls.append((raw_url, gist['id']))
        return raw_urls

    async def _get_gists(self):
        headers = {'Authorization': 'token {}'.format(self.key)}
        async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            return json.loads(await self._fetch(session, 'https://api.github.com/gists'))

    async def _delete_gists(self, gist_ids):
        headers = {'Authorization': 'token {}'.format(self.key)}
        for _id in gist_ids:
            async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                await self._delete(session, 'https://api.github.com/gists/{}'.format(_id))

    @staticmethod
    async def _fetch(session, url):
        async with session.get(url) as response:
            return await response.text()

    @staticmethod
    async def _post(session, url, body):
        async with session.post(url, json=body) as response:
            return await response.text()

    async def _wait_for_paw(self, paw, comm_type):
        for gist in await self._get_gists():
            if '{}-{}'.format(comm_type, paw) == gist['description']:
                return True
        return False

    @staticmethod
    async def _delete(session, url):
        async with session.delete(url) as response:
            return await response.text('ISO-8859-1')

    @staticmethod
    def encode_string(s):
        return str(b64encode(s), 'utf-8')
