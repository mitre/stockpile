"""Tests for hook.py (the plugin entry point)."""

import importlib.util
import sys
from unittest.mock import MagicMock, AsyncMock, patch

import pytest


def _load_hook():
    path = '/tmp/stockpile-pytest/hook.py'
    spec = importlib.util.spec_from_file_location('hook', path)
    mod = importlib.util.module_from_spec(spec)

    # Shim the stockpile service import for hook.py
    svc_mock = MagicMock()
    sys.modules['plugins.stockpile.app.stockpile_svc'] = MagicMock(
        StockpileService=svc_mock)

    spec.loader.exec_module(mod)
    return mod, svc_mock


class TestHook:

    def test_module_attributes(self):
        mod, _ = _load_hook()
        assert mod.name == 'Stockpile'
        assert mod.description
        assert mod.address == '/plugin/stockpile/gui'

    @pytest.mark.asyncio
    async def test_enable_registers_route(self):
        mod, svc_cls = _load_hook()
        mock_svc_instance = MagicMock()
        mock_svc_instance.data_svc = MagicMock()
        mock_svc_instance.data_svc.store = AsyncMock()
        svc_cls.return_value = mock_svc_instance

        app_svc = MagicMock()
        app_svc.application.router.add_route = MagicMock()

        file_svc = AsyncMock()
        file_svc.add_special_payload = AsyncMock()

        services = MagicMock()
        services.get = MagicMock(side_effect=lambda k: {
            'app_svc': app_svc,
            'file_svc': file_svc,
        }.get(k, MagicMock()))

        await mod.enable(services)

        app_svc.application.router.add_route.assert_called_once_with(
            'GET', '/plugin/stockpile/gui', mock_svc_instance.splash)
        file_svc.add_special_payload.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_enable_stores_obfuscators(self):
        mod, svc_cls = _load_hook()
        mock_svc_instance = MagicMock()
        mock_svc_instance.data_svc = MagicMock()
        mock_svc_instance.data_svc.store = AsyncMock()
        svc_cls.return_value = mock_svc_instance

        services = MagicMock()
        services.get = MagicMock(return_value=MagicMock(
            application=MagicMock(router=MagicMock()),
            add_special_payload=AsyncMock(),
        ))

        await mod.enable(services)

        # 4 obfuscators are registered
        assert mock_svc_instance.data_svc.store.await_count == 4

    @pytest.mark.asyncio
    async def test_enable_registers_donut_handler(self):
        mod, svc_cls = _load_hook()
        mock_svc_instance = MagicMock()
        mock_svc_instance.data_svc = MagicMock()
        mock_svc_instance.data_svc.store = AsyncMock()
        svc_cls.return_value = mock_svc_instance

        file_svc = AsyncMock()
        file_svc.add_special_payload = AsyncMock()

        services = MagicMock()
        services.get = MagicMock(side_effect=lambda k: {
            'app_svc': MagicMock(application=MagicMock(router=MagicMock())),
            'file_svc': file_svc,
        }.get(k, MagicMock()))

        await mod.enable(services)

        file_svc.add_special_payload.assert_awaited_once_with(
            '.donut', 'plugins.stockpile.app.donut.donut_handler')
