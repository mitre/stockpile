from app.utility.base_obfuscator import BaseObfuscator


class Obfuscation(BaseObfuscator):

    @property
    def supported_platforms(self):
        return dict(
            darwin=['sh'],
            linux=['sh']
        )

    def __init__(self, agent):
        self.agent = agent

    """ EXECUTORS """

    def sh(self, link):
        decryption_key = self.generate_name(size=20)
        #encrypted_command = 'curl -X POST -H "Content-Type: application/json" localhost:8888/generic -d \'{"link":"%s"}\' -H "function:get_link_key";echo %s | openssl aes-256-cbc -a -d -salt -k $x' % (self.decode_bytes(link.command), link.unique)
        #print(encrypted_command)
        #return encrypted_command
