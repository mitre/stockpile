import json
import aioftp
import logging

from app.interfaces.c2_active_interface import C2Active


class FTP(C2Active):

    logging.getLogger('aioftp').setLevel(logging.WARNING)

    def __init__(self, services, config):
        super().__init__(config=config, services=services)
        self.username = config['config']['username']
        self.password = config['config']['password']
        self.host = config['config']['host']
        self.port = config['config']['port']
        self.log = self.file_svc.create_logger('FTPService')

    def get_config(self):
        """
        Returns this C2 objects api key
        :return: FTP server, port, username, password
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
        try:
            client = await self._make_ftp_connection(self.host, self.port, self.username, self.password)
            results = await self._get_file(client, 'result')
            client.close()
            return results
        except Exception as e:
            self.log.debug('Receiving results over c2 (%s) failed!' % self.name)
            return []

    async def get_beacons(self):
        """
        Retrieve all beacons from a particular FTP server
        :return: the beacons
        """
        try:
            client = await self._make_ftp_connection(self.host, self.port, self.username, self.password)
            beacons = await self._get_file(client, 'beacon')
            client.close()
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
        Post an instruction for the agent to execute on a known FTP server
        :param text: The instruction text for the agent to execute
        :param paw: The paw of the agent
        :return:
        """
        try:
            client = await self._make_ftp_connection(self.host, self.port, self.username, self.password)
            if await self._wait_for_paw(client=client, paw=paw, comm_type='instructions'):
                return
            async with client.upload_stream('instructions-{}'.format(paw), offset=0) as stream:
                await stream.write(text.encode())
            client.close()
        except Exception as e:
            self.log.warning('Posting instructions over c2 (%s) failed!' % self.name)

    async def start(self):
        """
        Starts a loop that will run FTP C2
        :return:
        """
        await self._start_default_c2_active_channel()

    """ PRIVATE """

    async def _get_file(self, client, comm_type):
        comms = []
        for path, info in (await client.list(recursive=True)):
            if comm_type in str(path):
                async with client.download_stream(path, offset=0) as stream:
                    data = await stream.read(int(info['size']))
                comms.append(await self._process_agent_comms(data))
        return comms

    async def _process_agent_comms(self, content):
        return json.loads(self.file_svc.decode_bytes(content))

    @staticmethod
    async def _make_ftp_connection(host, port, login, password):
        client = aioftp.Client()
        await client.connect(host=host, port=port)
        await client.login(user=login, password=password)
        return client

    @staticmethod
    async def _wait_for_paw(client, paw, comm_type):
        for path, info in (await client.list(recursive=True)):
            if '{}-{}'.format(comm_type, paw) in str(path):
                return True
        return False
