"""Exhaustive tests for all packers in app/packers/."""

import importlib.util
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, mock_open

import pytest


def _load_packer(name):
    path = f'/tmp/stockpile-pytest/app/packers/{name}.py'
    spec = importlib.util.spec_from_file_location(f'packers.{name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===== gohide packer =====

class TestGohidePacker:

    @pytest.fixture
    def mod(self):
        return _load_packer('gohide')

    def test_module_name(self, mod):
        assert mod.name == 'gohide'

    @pytest.mark.asyncio
    async def test_check_dependencies_always_true(self, mod):
        result = await mod.check_dependencies(MagicMock())
        assert result is True

    def test_get_random_replacement_length(self, mod):
        packer = mod.Packer(file_svc=MagicMock())
        result = packer.get_random_replacement('hello')
        assert len(result) == 5
        assert isinstance(result, bytes)

    def test_get_random_replacement_alphanumeric(self, mod):
        packer = mod.Packer(file_svc=MagicMock())
        for _ in range(20):
            result = packer.get_random_replacement('test')
            assert result.decode('utf-8').isalnum()

    @pytest.mark.asyncio
    async def test_pack_replaces_go_build_id(self, mod):
        file_svc = MagicMock()
        file_svc.log = MagicMock()
        packer = mod.Packer(file_svc=file_svc)
        contents = b'Go build ID: "abc123"'
        filename, result = await packer.pack('binary', contents)
        assert b'Go build ID: "' not in result
        assert filename == 'binary'

    @pytest.mark.asyncio
    async def test_pack_replaces_paths(self, mod):
        file_svc = MagicMock()
        file_svc.log = MagicMock()
        packer = mod.Packer(file_svc=file_svc)
        contents = b'/mitre/something /caldera/other /sandcat/bin /gocat/files'
        filename, result = await packer.pack('test_binary', contents)
        assert b'/mitre/' not in result
        assert b'/caldera/' not in result

    @pytest.mark.asyncio
    async def test_pack_replaces_strings(self, mod):
        file_svc = MagicMock()
        file_svc.log = MagicMock()
        packer = mod.Packer(file_svc=file_svc)
        contents = b'github.com/mitre/caldera'
        filename, result = await packer.pack('test', contents)
        assert b'github.com' not in result

    @pytest.mark.asyncio
    async def test_pack_no_matching_content(self, mod):
        file_svc = MagicMock()
        file_svc.log = MagicMock()
        packer = mod.Packer(file_svc=file_svc)
        contents = b'nothing to replace here'
        filename, result = await packer.pack('test', contents)
        assert result == contents

    def test_packer_paths(self, mod):
        packer = mod.Packer(file_svc=MagicMock())
        assert 'mitre' in packer.paths
        assert 'caldera' in packer.paths
        assert 'sandcat' in packer.paths
        assert 'gocat' in packer.paths

    def test_packer_strings(self, mod):
        packer = mod.Packer(file_svc=MagicMock())
        assert 'github.com' in packer.strings


# ===== upx packer =====

class TestUpxPacker:

    @pytest.fixture
    def mod(self):
        return _load_packer('upx')

    def test_module_name(self, mod):
        assert mod.name == 'upx'

    @pytest.mark.asyncio
    async def test_check_dependencies(self, mod):
        app_svc = AsyncMock()
        app_svc.validate_requirement = AsyncMock(return_value=True)
        result = await mod.check_dependencies(app_svc)
        assert result is True

    @pytest.mark.asyncio
    async def test_pack_success(self, mod):
        file_svc = MagicMock()
        file_svc.log = MagicMock()
        packer = mod.Packer(file_svc=file_svc)
        packer.packer_folder = '/tmp/test_upx_packer'

        os.makedirs(packer.packer_folder, exist_ok=True)
        packed_contents = b'packed binary data'

        async def fake_communicate():
            # Write the "packed" file
            packed_path = os.path.join(packer.packer_folder, 'testfile')
            with open(packed_path, 'wb') as f:
                f.write(packed_contents)
            return b'', b''

        mock_process = MagicMock()
        mock_process.communicate = fake_communicate
        mock_process.returncode = 0

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            filename, result = await packer.pack('testfile', b'original data')
        assert filename == 'testfile'
        assert result == packed_contents

        # Cleanup
        import shutil
        if os.path.exists(packer.packer_folder):
            shutil.rmtree(packer.packer_folder)

    @pytest.mark.asyncio
    async def test_pack_failure_raises(self, mod):
        file_svc = MagicMock()
        file_svc.log = MagicMock()
        packer = mod.Packer(file_svc=file_svc)
        packer.packer_folder = '/tmp/test_upx_fail'
        os.makedirs(packer.packer_folder, exist_ok=True)

        async def fake_communicate():
            return b'', b'upx error'

        mock_process = MagicMock()
        mock_process.communicate = fake_communicate
        mock_process.returncode = 1

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(Exception, match='Error encountered when packing'):
                await packer.pack('testfile', b'data')

        import shutil
        if os.path.exists(packer.packer_folder):
            shutil.rmtree(packer.packer_folder)

    @pytest.mark.asyncio
    async def test_pack_cleans_up_on_failure(self, mod):
        file_svc = MagicMock()
        file_svc.log = MagicMock()
        packer = mod.Packer(file_svc=file_svc)
        packer.packer_folder = '/tmp/test_upx_cleanup'
        os.makedirs(packer.packer_folder, exist_ok=True)

        async def fake_communicate():
            return b'', b'error'

        mock_process = MagicMock()
        mock_process.communicate = fake_communicate
        mock_process.returncode = 1

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(Exception):
                await packer.pack('testfile', b'data')

        packed_file = os.path.join(packer.packer_folder, 'testfile')
        assert not os.path.exists(packed_file)

        import shutil
        if os.path.exists(packer.packer_folder):
            shutil.rmtree(packer.packer_folder)

    def test_packer_folder_default(self, mod):
        packer = mod.Packer(file_svc=MagicMock())
        assert packer.packer_folder == 'data/payloads'
