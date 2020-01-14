import json
import uuid
import os

from aiohttp import web
from datetime import datetime
from urllib.parse import urlparse

from app.interfaces.c2_passive_interface import C2Passive


class HTTP(C2Passive):

    def __init__(self, services, config):
        super().__init__(config=config)
        self.app = services.get('app_svc').application
        self.contact_svc = services.get('contact_svc')
        self.file_svc = services.get('file_svc')

    async def start(self):
        self.app.router.add_route('POST', '/ping', self._ping)
        self.app.router.add_route('POST', '/instructions', self._instructions)
        self.app.router.add_route('POST', '/results', self._results)
        self.app.router.add_route('*', '/file/download', self.download)
        self.app.router.add_route('POST', '/file/upload', self.upload_exfil_http)

    def valid_config(self):
        if hasattr(self.app, 'router'):
            return True
        return False

    """ PRIVATE """

    async def _ping(self, request):
        return web.Response(text=self.contact_svc.encode_string('pong'))

    async def _instructions(self, request):
        data = json.loads(self.contact_svc.decode_bytes(await request.read()))
        url = urlparse(data['server'])
        port = '443' if url.scheme == 'https' else 80
        data['server'] = '%s://%s:%s' % (url.scheme, url.hostname, url.port if url.port else port)
        data['c2'] = 'http'
        agent = await self.contact_svc.handle_heartbeat(**data)
        instructions = await self.contact_svc.get_instructions(data['paw'])
        response = dict(sleep=await agent.calculate_sleep(), instructions=instructions)
        return web.Response(text=self.contact_svc.encode_string(json.dumps(response)))

    async def _results(self, request):
        data = json.loads(self.contact_svc.decode_bytes(await request.read()))
        data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = await self.contact_svc.save_results(data['id'], data['output'], data['status'], data['pid'])
        return web.Response(text=self.contact_svc.encode_string(status))

    async def download(self, request):
        """
        Accept a request with a required header, file, and an optional header, platform, and download the file.
        :param request:
        :return: a multipart file via HTTP
        """
        try:
            payload = display_name = request.headers.get('file')
            payload, content, display_name = await self.file_svc.get_file(payload, request.headers.get('platform'))

            headers = dict([('CONTENT-DISPOSITION', 'attachment; filename="%s"' % display_name)])
            return web.Response(body=content, headers=headers)
        except FileNotFoundError:
            return web.HTTPNotFound(body='File not found')
        except Exception as e:
            return web.HTTPNotFound(body=str(e))

    async def save_multipart_file_upload(self, request, target_dir):
        """
        Accept a multipart file via HTTP and save it to the server
        :param request:
        :param target_dir: The path of the directory to save the uploaded file to.
        """
        try:
            reader = await request.multipart()
            while True:
                field = await reader.next()
                if not field:
                    break
                filename = field.filename
                with open(os.path.join(target_dir, filename), 'wb') as f:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
                self.log.debug('Uploaded file %s' % filename)
            return web.Response()
        except Exception as e:
            self.log.debug('Exception uploading file %s' % e)

    async def upload_exfil_http(self, request):
        dir_name = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        exfil_dir = await self.file_svc._create_exfil_sub_directory(dir_name=dir_name)
        return await self.save_multipart_file_upload(request, exfil_dir)
