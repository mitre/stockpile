import glob

from shutil import which
from aiohttp_jinja2 import template

from app.service.auth_svc import red_authorization


class StockpileService:

    def __init__(self, services):
        self.auth_svc = services.get('auth_svc')
        self.file_svc = services.get('file_svc')
        self.data_svc = services.get('data_svc')
        self.contact_svc = services.get('contact_svc')

    @red_authorization
    @template('stockpile.html')
    async def splash(self, request):
        abilities = [a for a in await self.data_svc.locate('abilities') if await a.which_plugin() == 'stockpile']
        adversaries = [a for a in await self.data_svc.locate('adversaries') if await a.which_plugin() == 'stockpile']
        return dict(abilities=abilities, adversaries=adversaries)

    async def dynamically_compile(self, headers):
        name, platform = headers.get('file'), headers.get('platform')
        if which('go') is not None:
            plugin, file_path = await self.file_svc.find_file_path(name)
            output = 'plugins/%s/data/payloads/%s-%s' % (plugin, name, platform)
            await self.file_svc.compile_go(platform, output, file_path)
        return '%s-%s' % (name, platform), '%s-%s' % (name, platform)

    async def load_c2_config(self, directory):
        c2_configs = {}
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for c2 in self.data_svc.strip_yml(filename):
                c2_configs[c2['name']] = c2
        return c2_configs
