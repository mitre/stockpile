"""Regression test for issue mitre/caldera#3097: stray semicolons in ability YAML."""
import os
import re
import glob
import yaml
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABILITIES_ROOT = os.path.join(REPO_ROOT, 'data', 'abilities')


def _iter_commands():
    for yml_path in glob.glob(f'{ABILITIES_ROOT}/**/*.yml', recursive=True):
        with open(yml_path) as fh:
            try:
                entries = yaml.safe_load(fh) or []
            except yaml.YAMLError:
                continue
        for entry in entries:
            for platform, execs in (entry.get('platforms') or {}).items():
                for exec_name, exec_def in (execs or {}).items():
                    cmd = (exec_def or {}).get('command', '') or ''
                    yield yml_path, platform, exec_name, cmd


@pytest.mark.parametrize('yml_path,platform,exec_name,cmd', list(_iter_commands()))
def test_no_double_semicolon(yml_path, platform, exec_name, cmd):
    """No ability command should contain a stray '; ;' double-semicolon."""
    assert not re.search(r';\s+;', cmd), (
        f"Double semicolon in {yml_path} [{platform}/{exec_name}]: {cmd!r}"
    )
