"""Regression test for issue mitre/caldera#3097: stray semicolons in ability YAML."""
import os
import re
import glob
import warnings
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABILITIES_ROOT = os.path.join(REPO_ROOT, 'data', 'abilities')


def _iter_commands():
    """Yield (yml_path, platform, exec_name, cmd) tuples from all ability YAML files.

    Glob results are sorted for deterministic ordering across runs.
    Files are opened with explicit UTF-8 encoding.
    YAML parse errors propagate as AssertionErrors with a clear message.
    Non-list, non-dict top-level data is skipped with a warning rather than
    raising an AttributeError.
    """
    paths = sorted(glob.glob(f'{ABILITIES_ROOT}/**/*.yml', recursive=True))
    for yml_path in paths:
        with open(yml_path, encoding='utf-8') as fh:
            try:
                data = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                raise AssertionError(f"YAML parse error in {yml_path}: {exc}") from exc
        if isinstance(data, dict):
            entries = [data]
        elif isinstance(data, list):
            entries = data or []
        else:
            warnings.warn(
                f"Skipping {yml_path}: unexpected top-level type {type(data).__name__}",
                stacklevel=2,
            )
            continue
        for entry in entries:
            for platform, execs in (entry.get('platforms') or {}).items():
                for exec_name, exec_def in (execs or {}).items():
                    cmd = (exec_def or {}).get('command', '') or ''
                    yield yml_path, platform, exec_name, cmd


def test_no_double_semicolon_in_all_abilities():
    """No ability command should contain a stray '; ;' double-semicolon.

    This test iterates all ability YAML files in a single test function to
    avoid eager loading at collection time (which would be triggered by
    @pytest.mark.parametrize with list(_iter_commands()) at module scope).
    """
    failures = []
    for yml_path, platform, exec_name, cmd in _iter_commands():
        if re.search(r';\s+;', cmd):
            failures.append(
                f"Double semicolon in {yml_path} [{platform}/{exec_name}]: {cmd!r}"
            )
    assert not failures, "\n".join(failures)
