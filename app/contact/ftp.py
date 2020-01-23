import json
import uuid
import aiohttp
import re
import asyncio
import aioftp


from app.interfaces.c2_active_interface import C2Active


class FTP(C2Active):

    def __init__(self, services, config):
        super().__init__(config=config, services=services)
        self.username = config['config']['username']
        self.password = config['config']['password']
        self.host = config['config']['host']
        self.log = self.file_svc.create_logger('FTPService')

    def get_config(self):
        """
        Returns this C2 objects api key
        :return: GIST api key
        """
        return 'TODO'

    def valid_config(self):
        #TODO
        return True

    async def get_results(self):
        """
        Retrieve all GIST posted results for a this C2's api key
        :return:
        """
        #TODO
        return []

    async def get_beacons(self):
        """
        Retrieve all GIST beacons for a particular api key
        :return: the beacons
        """
        try:
            beacons = await self._get_file(self.host, 21, self.username, self.password)
            return beacons
        except Exception as e:
            self.log.debug('Receiving beacons over c2 (%s) failed!' % self.name)
            return []

    async def post_payloads(self, payloads, paw):
        """
        Given a list of payloads and an agent paw, posts the payloads as a series of base64 encoded
        files attached to a single gist
        :param payloads:
        :param paw:
        :return:
        """
        try:
            files = {payload[0]: dict(content=self._encode_string(payload[1])) for payload in payloads}
            if len(files) < 1 or await self._wait_for_paw(paw, comm_type='payloads'):
                return
            gist = self._build_gist_content(comm_type='payloads', paw=paw, files=files)
            return await self._post_gist(gist)
        except Exception as e:
            self.log.warning('Posting payload over c2 (%s) failed! %s' % (self.name, e))

    async def post_instructions(self, text, paw):
        """
        Post an instruction for the agent to execute as an encoded GIST
        :param text: The instruction text for the agent to execute
        :param paw: The paw for the agent to execute
        :return:
        """
        try:
            if len(json.loads(self.file_svc.decode_bytes(text))['instructions']) < 1 or \
                    await self._wait_for_paw(paw, comm_type='instructions'):
                return
            gist = self._build_gist_content(comm_type='instructions', paw=paw,
                                            files={str(uuid.uuid4()): dict(content=text)})
            return await self._post_gist(gist)
        except Exception:
            self.log.warning('Posting instructions over c2 (%s) failed!' % self.name)

    async def start(self):
        """
        Starts a loop that will run GIST C2
        :return:
        """
        await self._start_default_c2_active_channel()

    """ PRIVATE """

    async def _list_dir(self, host, port, login, password):
        async with aioftp.ClientSession(host, port, login, password) as client:
            files = await client.list()
            return files

    async def _get_file(self, host, port, login, password):
        beacons = []
        async with aioftp.ClientSession(host, port, login, password) as client:
            for path, info in (await client.list(recursive=True)):
                if "beacon" in str(path):
                    async with client.download_stream(path, offset=0) as stream:
                        temp = b""
                        async for block in stream.iter_by_block():
                            temp = temp + block
                    beacons.append(await self._process_beacons(temp))
        return beacons

    async def _process_beacons(self, content):
        return json.loads(self.file_svc.decode_bytes(content))



