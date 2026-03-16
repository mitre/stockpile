"""Tests for app/stockpile_svc.py."""

import importlib.util
from unittest.mock import MagicMock, AsyncMock, patch

import pytest


def _load_service():
    path = '/tmp/stockpile-pytest/app/stockpile_svc.py'
    spec = importlib.util.spec_from_file_location('stockpile_svc', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StockpileService, mod


class TestStockpileService:
    Cls, _mod = _load_service()

    def _make_svc(self):
        services = {
            'auth_svc': MagicMock(),
            'file_svc': AsyncMock(),
            'data_svc': MagicMock(),
            'contact_svc': MagicMock(),
        }
        return self.Cls(services), services

    def test_init(self):
        svc, services = self._make_svc()
        assert svc.auth_svc is services['auth_svc']
        assert svc.file_svc is services['file_svc']
        assert svc.data_svc is services['data_svc']
        assert svc.contact_svc is services['contact_svc']

    @pytest.mark.asyncio
    async def test_splash(self):
        svc, _ = self._make_svc()
        result = await svc.splash(MagicMock())
        assert result == dict()

    @pytest.mark.asyncio
    @patch('shutil.which', return_value='/usr/bin/go')
    async def test_dynamically_compile_with_go(self, mock_which):
        svc, services = self._make_svc()
        services['file_svc'].find_file_path = AsyncMock(return_value=('stockpile', '/path/to/file'))
        services['file_svc'].compile_go = AsyncMock()
        headers = {'file': 'agent', 'platform': 'linux'}
        name, result = await svc.dynamically_compile(headers)
        assert name == 'agent-linux'
        assert result == 'agent-linux'
        services['file_svc'].compile_go.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dynamically_compile_no_go(self):
        svc, services = self._make_svc()
        headers = {'file': 'agent', 'platform': 'windows'}
        # Patch 'which' on the loaded module since it was imported via 'from shutil import which'
        with patch.object(self._mod, 'which', return_value=None):
            name, result = await svc.dynamically_compile(headers)
        assert name == 'agent-windows'
        assert result == 'agent-windows'

    @pytest.mark.asyncio
    async def test_load_c2_config_empty_dir(self):
        svc, services = self._make_svc()
        with patch('glob.iglob', return_value=[]):
            result = await svc.load_c2_config('/nonexistent')
        assert result == {}

    @pytest.mark.asyncio
    async def test_load_c2_config_with_files(self):
        svc, services = self._make_svc()
        services['data_svc'].strip_yml = MagicMock(return_value=[
            {'name': 'http', 'port': 8888},
        ])
        with patch('glob.iglob', return_value=['/dir/http.yml']):
            result = await svc.load_c2_config('/dir')
        assert 'http' in result
        assert result['http']['port'] == 8888

    @pytest.mark.asyncio
    async def test_load_c2_config_multiple_files(self):
        svc, services = self._make_svc()
        call_count = [0]

        def side_effect(filename):
            call_count[0] += 1
            if call_count[0] == 1:
                return [{'name': 'http', 'port': 8888}]
            return [{'name': 'tcp', 'port': 7777}]

        services['data_svc'].strip_yml = side_effect
        with patch('glob.iglob', return_value=['/dir/http.yml', '/dir/tcp.yml']):
            result = await svc.load_c2_config('/dir')
        assert len(result) == 2
