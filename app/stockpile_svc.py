import random
import string

from shutil import which


class SandService:

    def __init__(self, file_svc):
        self.file_svc = file_svc
        self.log = file_svc.add_service('sand_svc', self)

    async def dynamically_compile(self, headers):
        name, platform = headers.get('file'), headers.get('platform')
        if which('go') is not None:
            plugin, file_path = await self.file_svc.find_file_path(name)
            await self._change_file_hash(file_path)
            output = 'plugins/%s/payloads/%s-%s' % (plugin, name, platform)
            self.log.debug('Dynamically compiling %s' % name)
            await self.file_svc.compile_go(platform, output, file_path)
        return '%s-%s' % (name, platform)

    """ PRIVATE """

    @staticmethod
    async def _change_file_hash(file_path, size=30):
        key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(size))
        lines = open(file_path, 'r').readlines()
        lines[-1] = 'var key = "%s"' % key
        out = open(file_path, 'w')
        out.writelines(lines)
        out.close()
        return key
