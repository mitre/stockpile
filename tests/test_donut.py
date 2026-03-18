"""Tests for app/donut.py."""

import base64
import importlib.util
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, mock_open

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True, scope='module')
def _donut_module_shim(tmp_path_factory):
    """Install a fake 'donut' package into sys.modules for the duration of the
    module, then remove it on teardown so other test modules are not polluted."""
    shim = types.ModuleType('donut')
    shim.create = MagicMock(return_value=b'\x00\x01\x02shellcode')
    sys.modules['donut'] = shim
    yield shim
    sys.modules.pop('donut', None)


def _load_donut():
    path = _REPO_ROOT / 'app' / 'donut.py'
    spec = importlib.util.spec_from_file_location('donut_handler_mod', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestDonutHandler:
    mod = _load_donut()

    @pytest.mark.asyncio
    async def test_donut_handler_with_exe(self):
        file_svc = AsyncMock()
        file_svc.find_file_path = AsyncMock(return_value=('plugin', '/path/to/Rubeus.donut.exe'))
        data_svc = AsyncMock()
        data_svc.locate = AsyncMock(return_value=[])
        services = {'file_svc': file_svc, 'data_svc': data_svc}
        args = {'file': 'Rubeus.donut', 'X-Link-Id': None}

        with patch.object(self.mod, '_write_shellcode_to_file') as mock_write:
            result = await self.mod.donut_handler(services, args)
        assert result == ('Rubeus.donut', 'Rubeus.donut')
        mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_donut_handler_no_exe(self):
        file_svc = AsyncMock()
        file_svc.find_file_path = AsyncMock(return_value=('plugin', None))
        services = {'file_svc': file_svc, 'data_svc': AsyncMock()}
        args = {'file': 'Missing.donut', 'X-Link-Id': None}

        result = await self.mod.donut_handler(services, args)
        assert result == ('Missing.donut', 'Missing.donut')

    @pytest.mark.asyncio
    async def test_get_exe_path_donut_exe(self):
        file_svc = AsyncMock()
        file_svc.find_file_path = AsyncMock(side_effect=[
            ('plugin', '/path/Rubeus.donut.exe'),
        ])
        services = {'file_svc': file_svc}
        result = await self.mod._get_exe_path(services, 'Rubeus.donut')
        assert result == '/path/Rubeus.donut.exe'

    @pytest.mark.asyncio
    async def test_get_exe_path_fallback(self):
        file_svc = AsyncMock()
        file_svc.find_file_path = AsyncMock(side_effect=[
            ('plugin', None),
            ('plugin', '/path/Rubeus.exe'),
        ])
        services = {'file_svc': file_svc}
        result = await self.mod._get_exe_path(services, 'Rubeus.donut')
        assert result == '/path/Rubeus.exe'

    @pytest.mark.asyncio
    async def test_get_exe_path_not_found(self):
        file_svc = AsyncMock()
        file_svc.find_file_path = AsyncMock(return_value=('plugin', None))
        services = {'file_svc': file_svc}
        result = await self.mod._get_exe_path(services, 'NotFound.donut')
        assert result is None

    def test_write_shellcode_to_file(self):
        m = mock_open()
        with patch('builtins.open', m):
            self.mod._write_shellcode_to_file(b'\x00\x01', '/tmp/test.donut')
        m.assert_called_once_with('/tmp/test.donut', 'wb')
        m().write.assert_called_once_with(b'\x00\x01')

    def test_write_shellcode_handles_exception(self):
        with patch('builtins.open', side_effect=PermissionError('denied')):
            # Should not raise
            self.mod._write_shellcode_to_file(b'\x00', '/bad/path')

    @pytest.mark.asyncio
    async def test_get_parameters_no_operations(self):
        data_svc = AsyncMock()
        data_svc.locate = AsyncMock(return_value=[])
        result = await self.mod._get_parameters(data_svc, 'test.donut')
        assert result == ''

    @pytest.mark.asyncio
    async def test_get_parameters_with_link_id(self):
        link = MagicMock()
        link.id = 'link-1'
        link.decide = 1
        link.command = base64.b64encode(b'test.donut -arg1 value1').decode()
        link.ability = MagicMock(name='test_ability')
        operation = MagicMock()
        operation.chain = [link]
        operation.obfuscator = 'plain-text'
        operation.has_link = MagicMock(return_value=True)
        data_svc = AsyncMock()
        data_svc.locate = AsyncMock(return_value=[operation])
        result = await self.mod._get_parameters(data_svc, 'test.donut', link_id='link-1')
        assert '-arg1' in result
        assert 'value1' in result

    @pytest.mark.asyncio
    async def test_get_parameters_without_link_id(self):
        link = MagicMock()
        link.id = 'link-2'
        link.decide = 1
        link.finish = None
        link.executor = MagicMock()
        link.executor.name = 'donut_executor'
        link.executor.payloads = ['payload.donut']
        link.command = base64.b64encode(b'payload.donut --flag').decode()
        link.ability = MagicMock(name='test')
        operation = MagicMock()
        operation.chain = [link]
        operation.obfuscator = 'plain-text'
        operation.has_link = MagicMock(return_value=True)
        data_svc = AsyncMock()
        data_svc.locate = AsyncMock(return_value=[operation])
        result = await self.mod._get_parameters(data_svc, 'payload.donut')
        assert '--flag' in result
