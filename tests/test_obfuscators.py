import unittest
from random import seed

from app.objects.c_agent import Agent
from app.objects.secondclass.c_link import Link
from app.objects.c_ability import Ability
from app.obfuscators.base64_basic import Obfuscation as Base64Obfuscator
from app.obfuscators.plain_text import Obfuscation as PlainTextObfuscator
from app.obfuscators.base64_jumble import Obfuscation as Base64JumbleObfuscator
from app.obfuscators.caesar_cipher import Obfuscation as CaesarCipherObfuscator


class TestObfuscators(unittest.TestCase):

    def setUp(self):
        self.command = 'd2hvYW1p'
        self.dummy_ability = Ability(ability_id=None, tactic=None, technique_id=None, technique=None, name=None,
                                     test=None, description=None, cleanup=None, executor='sh', platform=None,
                                     payload=None, variations=[], parsers=None, requirements=None, privilege=None)
        self.dummy_agent = Agent(paw='123', platform='linux', executors=['sh'], server='http://localhost:8888',
                                 sleep_min=0, sleep_max=0, watchdog=0)
        self.dummy_link = Link(id='abc', operation='123', command=self.command, paw='123', ability=self.dummy_ability)

    def test_plain_text(self):
        o = PlainTextObfuscator(self.dummy_agent)
        obfuscated_command = o.run(self.dummy_link)
        self.assertEqual('whoami', obfuscated_command)

    def test_base64_basic(self):
        o = Base64Obfuscator(self.dummy_agent)
        obfuscated_command = o.run(self.dummy_link)
        self.assertEqual('eval "$(echo %s | base64 --decode)"' % self.command, obfuscated_command)

    def test_base64_jumble(self):
        o = Base64JumbleObfuscator(self.dummy_agent)
        obfuscated_command = o.run(self.dummy_link)
        actual_cmd = obfuscated_command.split()[2]
        self.assertEqual(len(self.command) + 1, len(actual_cmd))

    def test_caesar_cipher(self):
        seed(1)
        self.dummy_ability.executor = 'psh'
        self.dummy_agent.platform = 'windows'
        self.dummy_agent.executors[0] = 'psh'

        o = CaesarCipherObfuscator(self.dummy_agent)
        obfuscated_command = o.run(self.dummy_link)
        actual_cmd = obfuscated_command.split()[2][:-1]
        self.assertEqual(len(self.dummy_link.command), len(actual_cmd))


if __name__ == '__main__':
    unittest.main()
