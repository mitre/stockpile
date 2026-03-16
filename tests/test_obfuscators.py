"""Exhaustive tests for all obfuscators in app/obfuscators/."""

import base64
import importlib.util
from unittest.mock import MagicMock, patch

import pytest


def _load_obfuscator(name):
    path = f'/tmp/stockpile-pytest/app/obfuscators/{name}.py'
    spec = importlib.util.spec_from_file_location(f'obfuscators.{name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Obfuscation


def _make_link(command_text='whoami'):
    """Create a mock link whose .command is the base64 of command_text."""
    encoded = base64.b64encode(command_text.encode()).decode()
    link = MagicMock()
    link.command = encoded
    link.id = 'link-123'
    return link


# ===== base64_jumble =====

class TestBase64Jumble:
    Cls = _load_obfuscator('base64_jumble')

    def test_supported_platforms(self):
        o = self.Cls()
        sp = o.supported_platforms
        assert 'windows' in sp
        assert 'darwin' in sp
        assert 'linux' in sp
        assert 'psh' in sp['windows']
        assert 'sh' in sp['darwin']

    def test_run_jumbles_command(self):
        o = self.Cls()
        link = _make_link('echo hello')
        original_cmd = link.command
        o.run(link)
        # After jumbling, command should not be valid base64 anymore
        assert not o.is_base64(link.command)

    def test_sh_wraps_command(self):
        o = self.Cls()
        link = _make_link('whoami')
        o.run(link)
        result = o.sh(link, extra=1)
        assert 'eval' in result
        assert 'base64 --decode' in result

    def test_psh_wraps_command(self):
        o = self.Cls()
        link = _make_link('whoami')
        o.run(link)
        result = o.psh(link, extra=1)
        assert 'powershell -Enc' in result

    def test_random_char_is_alphanumeric(self):
        o = self.Cls()
        for _ in range(50):
            c = o._random_char()
            assert c.isalnum()

    def test_jumble_adds_characters(self):
        o = self.Cls()
        cmd = base64.b64encode(b'test').decode()
        jumbled, extra = o._jumble_command(cmd)
        assert extra >= 0
        assert len(jumbled) >= len(cmd)

    def test_psh_handles_binascii_error(self):
        """When the jumbled command can't be decoded, the psh method
        should fall back to stripping extra chars."""
        o = self.Cls()
        link = _make_link('test command')
        o.run(link)
        # This should not raise
        result = o.psh(link, extra=1)
        assert 'powershell' in result


# ===== base64_no_padding =====

class TestBase64NoPadding:
    Cls = _load_obfuscator('base64_no_padding')

    def test_supported_platforms(self):
        o = self.Cls()
        sp = o.supported_platforms
        assert 'windows' in sp
        assert 'darwin' in sp
        assert 'linux' in sp

    def test_run_removes_padding(self):
        o = self.Cls()
        link = _make_link('hello')
        # base64 of 'hello' is 'aGVsbG8=' (has padding)
        assert '=' in link.command
        o.run(link)
        assert '=' not in link.command

    def test_run_no_padding_present(self):
        o = self.Cls()
        # 'abc' -> base64 'YWJj' (no padding)
        link = _make_link('abc')
        original = link.command
        o.run(link)
        assert link.command == original

    def test_sh_output(self):
        o = self.Cls()
        link = _make_link('test')
        o.run(link)
        result = o.sh(link)
        assert 'eval' in result
        assert 'base64 --decode' in result
        assert '===' in result

    def test_psh_output(self):
        o = self.Cls()
        link = _make_link('test')
        o.run(link)
        result = o.psh(link)
        assert 'Invoke-Expression' in result
        assert 'FromBase64String' in result


# ===== caesar_cipher =====

class TestCaesarCipher:
    Cls = _load_obfuscator('caesar_cipher')

    def test_supported_platforms(self):
        o = self.Cls()
        sp = o.supported_platforms
        assert 'windows' in sp
        assert 'darwin' in sp
        assert 'linux' in sp

    def test_apply_cipher_shifts(self):
        o = self.Cls()
        encrypted, shift = o._apply_cipher('abc', bounds=26)
        assert shift >= 1
        assert shift <= 26
        # Decrypt
        decrypted = ''.join([chr(ord(c) - shift) if c.isalpha() else c for c in encrypted])
        assert decrypted == 'abc'

    def test_apply_cipher_non_alpha_unchanged(self):
        o = self.Cls()
        encrypted, shift = o._apply_cipher('a1b!c', bounds=26)
        assert encrypted[1] == '1'
        assert encrypted[3] == '!'

    def test_psh_output(self):
        o = self.Cls()
        link = _make_link('whoami')
        result = o.psh(link)
        assert '$encrypted' in result
        assert '$cmd' in result

    def test_sh_output(self):
        o = self.Cls()
        link = _make_link('whoami')
        result = o.sh(link)
        assert 'chr' in result
        assert 'ord' in result

    def test_cipher_roundtrip(self):
        """The cipher shifts alpha chars by a random amount; verify we can reverse it.
        Note: the cipher can shift chars outside the a-z/A-Z range, so we must
        use the same alpha-only condition used in the cipher itself."""
        o = self.Cls()
        original = 'HelloWorld'
        encrypted, shift = o._apply_cipher(original)
        # The original cipher only shifts .isalpha() chars, so the encrypted
        # chars may no longer be alpha. Reverse by subtracting shift from
        # every character that was originally alpha.
        decrypted = []
        for orig_c, enc_c in zip(original, encrypted):
            if orig_c.isalpha():
                decrypted.append(chr(ord(enc_c) - shift))
            else:
                decrypted.append(enc_c)
        assert ''.join(decrypted) == original

    def test_empty_string(self):
        o = self.Cls()
        encrypted, shift = o._apply_cipher('')
        assert encrypted == ''


# ===== steganography =====

class TestSteganography:
    Cls = _load_obfuscator('steganography')

    def test_supported_platforms(self):
        o = self.Cls()
        sp = o.supported_platforms
        assert 'darwin' in sp
        assert 'linux' in sp
        # steganography does NOT support windows
        assert 'windows' not in sp

    @patch('os.path.isfile', return_value=True)
    def test_sh_existing_file(self, mock_isfile):
        o = self.Cls()
        link = MagicMock()
        link.id = 'test-link-id'
        link.command = base64.b64encode(b'whoami').decode()
        result = o.sh(link)
        assert 'curl' in result
        assert 'meow-test-link-id.jpg' in result

    @patch('os.path.isfile', return_value=False)
    @patch('requests.get')
    def test_sh_downloads_image(self, mock_get, mock_isfile):
        o = self.Cls()
        link = MagicMock()
        link.id = 'dl-link'
        link.command = base64.b64encode(b'test').decode()

        mock_response = MagicMock()
        mock_response.json.return_value = {'file': 'http://example.com/cat.jpg'}
        mock_response.content = b'image-data'
        mock_get.return_value = mock_response

        import builtins
        from unittest.mock import mock_open
        m = mock_open()
        with patch.object(builtins, 'open', m):
            result = o.sh(link)
        assert 'curl' in result
