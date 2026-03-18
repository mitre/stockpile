import ast
import glob
import importlib
import inspect
import os
import re

import pytest
import yaml


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), '..')
ABILITIES_DIR = os.path.join(PLUGIN_DIR, 'data', 'abilities')
PAYLOADS_DIR = os.path.join(PLUGIN_DIR, 'payloads')
OBFUSCATORS_DIR = os.path.join(PLUGIN_DIR, 'app', 'obfuscators')
PARSERS_DIR = os.path.join(PLUGIN_DIR, 'app', 'parsers')

REQUIRED_ABILITY_FIELDS = {'id', 'name', 'tactic'}


class TestHookModule:
    """Tests that the stockpile hook.py module can be loaded and has expected attributes."""

    def test_hook_module_loads(self):
        hook_path = os.path.join(PLUGIN_DIR, 'hook.py')
        assert os.path.isfile(hook_path), 'hook.py not found'
        tree = ast.parse(open(hook_path).read())
        top_level_names = [
            node.id if isinstance(node, ast.Name) else node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert 'enable' in top_level_names, 'hook.py must define an enable() function'

    def test_hook_has_name_and_description(self):
        hook_path = os.path.join(PLUGIN_DIR, 'hook.py')
        source = open(hook_path).read()
        tree = ast.parse(source)
        assigned_names = [
            node.targets[0].id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        ]
        assert 'name' in assigned_names, 'hook.py should assign a name variable'
        assert 'description' in assigned_names, 'hook.py should assign a description variable'


class TestAbilitiesYAML:
    """Tests that all ability YAML files are valid and have required fields."""

    @staticmethod
    def _collect_yaml_files():
        pattern = os.path.join(ABILITIES_DIR, '**', '*.yml')
        return glob.glob(pattern, recursive=True)

    def test_abilities_directory_exists(self):
        assert os.path.isdir(ABILITIES_DIR), 'abilities directory not found'

    def test_at_least_one_ability_exists(self):
        files = self._collect_yaml_files()
        assert len(files) > 0, 'No ability YAML files found'

    def test_all_abilities_are_parseable(self):
        for yml_file in self._collect_yaml_files():
            with open(yml_file) as f:
                try:
                    data = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f'Failed to parse {yml_file}: {e}')
                assert data is not None, f'{yml_file} is empty'

    def test_all_abilities_have_required_fields(self):
        for yml_file in self._collect_yaml_files():
            with open(yml_file) as f:
                data = yaml.safe_load(f)
            if not isinstance(data, list):
                data = [data]
            for ability in data:
                for field in REQUIRED_ABILITY_FIELDS:
                    assert field in ability, (
                        f'{yml_file}: ability missing required field "{field}"'
                    )

    def test_all_abilities_have_technique_info(self):
        """Technique can be either a nested 'technique' dict or 'technique_id' + 'technique_name' fields."""
        for yml_file in self._collect_yaml_files():
            with open(yml_file) as f:
                data = yaml.safe_load(f)
            if not isinstance(data, list):
                data = [data]
            for ability in data:
                has_technique = 'technique' in ability
                has_technique_id = 'technique_id' in ability or 'technique_name' in ability
                assert has_technique or has_technique_id, (
                    f'{yml_file}: ability missing technique information '
                    '(need either "technique" dict or "technique_id"/"technique_name" fields)'
                )

    def test_ability_ids_are_unique(self):
        seen_ids = {}
        for yml_file in self._collect_yaml_files():
            with open(yml_file) as f:
                data = yaml.safe_load(f)
            if not isinstance(data, list):
                data = [data]
            for ability in data:
                aid = ability.get('id')
                if aid in seen_ids:
                    pytest.fail(
                        f'Duplicate ability id {aid} in {yml_file} and {seen_ids[aid]}'
                    )
                seen_ids[aid] = yml_file


class TestPayloads:
    """Tests that the payloads directory contains expected files."""

    def test_payloads_directory_exists(self):
        assert os.path.isdir(PAYLOADS_DIR), 'payloads directory not found'

    def test_payloads_not_empty(self):
        files = os.listdir(PAYLOADS_DIR)
        assert len(files) > 0, 'payloads directory is empty'

    def test_ragdoll_payload_exists(self):
        ragdoll = os.path.join(PAYLOADS_DIR, 'ragdoll.py')
        assert os.path.isfile(ragdoll), 'ragdoll.py payload not found'

    def test_scanner_payload_exists(self):
        scanner = os.path.join(PAYLOADS_DIR, 'scanner.py')
        assert os.path.isfile(scanner), 'scanner.py payload not found'


class TestObfuscators:
    """Tests that obfuscator modules load correctly."""

    EXPECTED_OBFUSCATORS = [
        'plain_text',
        'base64_basic',
        'base64_jumble',
        'base64_no_padding',
        'caesar_cipher',
        'steganography',
    ]

    def test_obfuscators_directory_exists(self):
        assert os.path.isdir(OBFUSCATORS_DIR), 'obfuscators directory not found'

    @pytest.mark.parametrize('module_name', EXPECTED_OBFUSCATORS)
    def test_obfuscator_file_exists(self, module_name):
        path = os.path.join(OBFUSCATORS_DIR, f'{module_name}.py')
        assert os.path.isfile(path), f'Obfuscator module {module_name}.py not found'

    @pytest.mark.parametrize('module_name', EXPECTED_OBFUSCATORS)
    def test_obfuscator_module_is_valid_python(self, module_name):
        path = os.path.join(OBFUSCATORS_DIR, f'{module_name}.py')
        with open(path) as f:
            try:
                ast.parse(f.read())
            except SyntaxError as e:
                pytest.fail(f'{module_name}.py has syntax error: {e}')

    @pytest.mark.parametrize('module_name', EXPECTED_OBFUSCATORS)
    def test_obfuscator_defines_obfuscation_class(self, module_name):
        path = os.path.join(OBFUSCATORS_DIR, f'{module_name}.py')
        with open(path) as f:
            tree = ast.parse(f.read())
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert 'Obfuscation' in class_names, (
            f'{module_name}.py should define an Obfuscation class'
        )


class TestParsers:
    """Tests that parser modules load correctly."""

    def test_parsers_directory_exists(self):
        assert os.path.isdir(PARSERS_DIR), 'parsers directory not found'

    def test_parsers_not_empty(self):
        py_files = [f for f in os.listdir(PARSERS_DIR) if f.endswith('.py') and f != '__init__.py']
        assert len(py_files) > 0, 'No parser modules found'

    def test_all_parsers_are_valid_python(self):
        for f in os.listdir(PARSERS_DIR):
            if f.endswith('.py') and not f.startswith('__'):
                path = os.path.join(PARSERS_DIR, f)
                with open(path) as fh:
                    try:
                        ast.parse(fh.read())
                    except SyntaxError as e:
                        pytest.fail(f'{f} has syntax error: {e}')


class TestSteganographySecurity:
    """Tests that steganography.py uses verify=True and has timeout on requests."""

    def _get_source(self):
        path = os.path.join(OBFUSCATORS_DIR, 'steganography.py')
        with open(path) as f:
            return f.read()

    def test_steganography_verify_flag(self):
        source = self._get_source()
        # Check for verify=False which is insecure
        matches = re.findall(r'verify\s*=\s*False', source)
        if matches:
            pytest.fail(
                f'steganography.py uses verify=False ({len(matches)} occurrence(s)). '
                'SSL verification should not be disabled.'
            )

    def test_steganography_requests_have_timeout(self):
        source = self._get_source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                is_requests_call = False
                if isinstance(func, ast.Attribute) and func.attr in ('get', 'post', 'put', 'delete', 'patch', 'head'):
                    if isinstance(func.value, ast.Name) and func.value.id == 'requests':
                        is_requests_call = True
                if is_requests_call:
                    keyword_names = [kw.arg for kw in node.keywords]
                    if 'timeout' not in keyword_names:
                        line = getattr(node, 'lineno', '?')
                        pytest.fail(
                            f'steganography.py line {line}: requests call missing timeout parameter'
                        )


class TestRagdollSecurity:
    """Tests that ragdoll.py has timeout on requests calls."""

    def _get_source(self):
        path = os.path.join(PAYLOADS_DIR, 'ragdoll.py')
        with open(path) as f:
            return f.read()

    def test_ragdoll_requests_have_timeout(self):
        source = self._get_source()
        tree = ast.parse(source)
        requests_methods = {'get', 'post', 'put', 'delete', 'patch', 'head'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                is_requests_call = False
                if isinstance(func, ast.Attribute) and func.attr in requests_methods:
                    if isinstance(func.value, ast.Name) and func.value.id == 'requests':
                        is_requests_call = True
                if is_requests_call:
                    keyword_names = [kw.arg for kw in node.keywords]
                    if 'timeout' not in keyword_names:
                        line = getattr(node, 'lineno', '?')
                        pytest.fail(
                            f'ragdoll.py line {line}: requests.{func.attr}() missing timeout parameter'
                        )
