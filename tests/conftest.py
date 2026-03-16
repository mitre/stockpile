"""Shared fixtures for stockpile test suite.

All Caldera internal objects are replaced by lightweight fakes so that
the tests never need a running Caldera server.
"""

import sys
import types
from unittest.mock import MagicMock, AsyncMock
from collections import defaultdict

import pytest


# ---------------------------------------------------------------------------
# Fake Caldera object stubs
# ---------------------------------------------------------------------------

class FakeFact:
    """Minimal stand-in for app.objects.secondclass.c_fact.Fact"""
    def __init__(self, trait=None, value=None, collected_by=None, relationships=None):
        self.trait = trait
        self.value = value
        self.collected_by = collected_by or []
        self.relationships = relationships or []

    def __eq__(self, other):
        if not isinstance(other, FakeFact):
            return NotImplemented
        return self.trait == other.trait and self.value == other.value

    def __repr__(self):
        return f"FakeFact(trait={self.trait!r}, value={self.value!r})"


class FakeRelationship:
    """Minimal stand-in for app.objects.secondclass.c_relationship.Relationship"""
    def __init__(self, source=None, edge=None, target=None, score=0):
        self.source = source
        self.edge = edge
        self.target = target
        self.score = score

    def __repr__(self):
        return (f"FakeRelationship(source={self.source!r}, edge={self.edge!r}, "
                f"target={self.target!r})")


class FakeMapper:
    """Represents a parser mapper entry."""
    def __init__(self, source='test.source', target='test.target', edge='has',
                 custom_parser_vals=None):
        self.source = source
        self.target = target
        self.edge = edge
        self.custom_parser_vals = custom_parser_vals or {}


class FakeLink:
    """Minimal stand-in for a Link object."""
    def __init__(self, command='', used=None, paw='abc', host='host1',
                 id='link-1', ability=None, status=0, relationships=None,
                 visibility=None, executor=None, score=0, finish=None, decide=None):
        self.command = command
        self.used = used or []
        self.paw = paw
        self.host = host
        self.id = id
        self.ability = ability
        self.status = status
        self.relationships = relationships or []
        self.visibility = visibility or MagicMock(score=50)
        self.executor = executor
        self.score = score
        self.finish = finish
        self.decide = decide


class FakeAgent:
    def __init__(self, paw='abc', host='host1', contact='http', trusted=True,
                 privilege='User', architecture='amd64'):
        self.paw = paw
        self.host = host
        self.contact = contact
        self.trusted = trusted
        self.privilege = privilege
        self.architecture = architecture

    async def get_preferred_executor(self, ability):
        return ability._executor if hasattr(ability, '_executor') else None

    async def capabilities(self, abilities):
        return abilities


class FakeAbility:
    def __init__(self, ability_id='ab-1', name='test_ability', requirements=None, _executor=None):
        self.ability_id = ability_id
        self.name = name
        self.requirements = requirements or []
        self._executor = _executor

    def __hash__(self):
        return hash(self.ability_id)

    def __eq__(self, other):
        if isinstance(other, FakeAbility):
            return self.ability_id == other.ability_id
        return NotImplemented


class FakeExecutor:
    def __init__(self, name='psh', platform='windows', command='', test='',
                 parsers=None, payloads=None):
        self.name = name
        self.platform = platform
        self.command = command
        self.test = test
        self.parsers = parsers or []
        self.payloads = payloads or []


class FakeParserConfig:
    def __init__(self, source='', target='', edge=''):
        self.source = source
        self.target = target
        self.edge = edge


class FakeParser:
    def __init__(self, parserconfigs=None):
        self.parserconfigs = parserconfigs or []


class FakeOperation:
    def __init__(self, chain=None, agents=None, adversary=None, obfuscator='plain-text',
                 planner=None, objective=None, auto_close=True, state='running'):
        self.chain = chain or []
        self.agents = agents or []
        self.adversary = adversary
        self.obfuscator = obfuscator
        self.planner = planner or MagicMock(name='atomic')
        self.objective = objective
        self.auto_close = auto_close
        self.state = state
        self._applied = []
        self._facts = []
        self._relationships = []

    async def apply(self, link):
        self._applied.append(link)
        return link.id if hasattr(link, 'id') else 'applied'

    async def wait_for_links_completion(self, link_ids):
        pass

    async def all_relationships(self):
        return self._relationships

    async def all_facts(self):
        return self._facts

    async def active_agents(self):
        return self.agents

    def has_link(self, link_id):
        return any(getattr(l, 'id', None) == link_id for l in self.chain)


class FakeAdversary:
    def __init__(self, adversary_id='adv-1', name='test_adversary', atomic_ordering=None):
        self.adversary_id = adversary_id
        self.name = name
        self.atomic_ordering = atomic_ordering or []


class FakeGoal:
    def __init__(self, target='', operator='==', value='', count=1):
        self.target = target
        self.operator = operator
        self.value = value
        self.count = count

    def satisfied(self, facts):
        return False


class FakeObjective:
    def __init__(self, goals=None):
        self.goals = goals or []


# ---------------------------------------------------------------------------
# Shim heavy Caldera imports so the plugin modules can be loaded without
# a full Caldera installation.
# ---------------------------------------------------------------------------

def _install_caldera_shims():
    """Register fake modules in sys.modules so that 'from app.objects...'
    imports resolve without Caldera being installed."""

    # Helper to create a module with arbitrary attributes
    def _make_mod(name, **attrs):
        mod = types.ModuleType(name)
        mod.__dict__.update(attrs)
        return mod

    modules_to_shim = {
        'app': _make_mod('app'),
        'app.objects': _make_mod('app.objects'),
        'app.objects.secondclass': _make_mod('app.objects.secondclass'),
        'app.objects.secondclass.c_fact': _make_mod(
            'app.objects.secondclass.c_fact', Fact=FakeFact),
        'app.objects.secondclass.c_relationship': _make_mod(
            'app.objects.secondclass.c_relationship', Relationship=FakeRelationship),
        'app.objects.secondclass.c_link': _make_mod(
            'app.objects.secondclass.c_link', Link=FakeLink),
        'app.objects.secondclass.c_executor': _make_mod(
            'app.objects.secondclass.c_executor', Executor=FakeExecutor),
        'app.objects.secondclass.c_goal': _make_mod(
            'app.objects.secondclass.c_goal', Goal=FakeGoal),
        'app.objects.c_obfuscator': _make_mod(
            'app.objects.c_obfuscator', Obfuscator=MagicMock),
        'app.objects.c_operation': _make_mod(
            'app.objects.c_operation', Operation=FakeOperation),
        'app.objects.c_ability': _make_mod(
            'app.objects.c_ability', Ability=FakeAbility),
        'app.objects.c_agent': _make_mod(
            'app.objects.c_agent', Agent=FakeAgent),
        'app.service': _make_mod('app.service'),
        'app.service.planning_svc': _make_mod(
            'app.service.planning_svc', PlanningService=MagicMock),
        'app.utility': _make_mod('app.utility'),
        'app.utility.base_world': _make_mod(
            'app.utility.base_world',
            BaseWorld=type('BaseWorld', (), {'Access': type('Access', (), {'APP': 0})})),
    }

    # BaseObfuscator shim
    class _BaseObfuscator:
        def run(self, link, **kwargs):
            return link
        @staticmethod
        def is_base64(s):
            import base64 as _b64
            try:
                if isinstance(s, str):
                    sb = bytes(s, 'ascii')
                elif isinstance(s, bytes):
                    sb = s
                else:
                    return False
                return _b64.b64encode(_b64.b64decode(sb)) == sb
            except Exception:
                return False
        @staticmethod
        def decode_bytes(s):
            import base64 as _b64
            return _b64.b64decode(s).decode('utf-8')
        @staticmethod
        def get_config(prop='', name=''):
            return 'http://localhost:8888'

    modules_to_shim['app.utility.base_obfuscator'] = _make_mod(
        'app.utility.base_obfuscator', BaseObfuscator=_BaseObfuscator)

    # BaseParser shim
    class _BaseParser:
        def __init__(self, parser_info=None):
            if parser_info:
                self.mappers = parser_info.get('mappers', [])
                self.used_facts = parser_info.get('used_facts', [])
                self.source_facts = parser_info.get('source_facts', [])
            else:
                self.mappers = []
                self.used_facts = []
                self.source_facts = []

        @staticmethod
        def line(blob):
            return blob.splitlines()

        @staticmethod
        def broadcastip(blob):
            import re
            results = []
            for m in re.finditer(r'broadcast (\d+\.\d+\.\d+\.\d+)', blob, re.IGNORECASE):
                results.append(m.group(1))
            if not results:
                for m in re.finditer(r'Bcast:(\d+\.\d+\.\d+\.\d+)', blob):
                    results.append(m.group(1))
            return results

        @staticmethod
        def filename(blob):
            import re
            return re.findall(r'[\w\-. ]+\.[\w]+', blob)

        @staticmethod
        def set_value(mapper_field, value, used_facts):
            return value

        @staticmethod
        def load_json(blob):
            import json
            try:
                return json.loads(blob)
            except Exception:
                return None

    modules_to_shim['app.utility.base_parser'] = _make_mod(
        'app.utility.base_parser', BaseParser=_BaseParser)

    # BaseService shim
    class _BaseService:
        def add_service(self, name, svc):
            return MagicMock()
    modules_to_shim['app.utility.base_service'] = _make_mod(
        'app.utility.base_service', BaseService=_BaseService)

    # BasePlanningService shim
    class _BasePlanningService:
        re_variable = r'#{(.*?)}'
        re_trait = r'^[^[]*'
    modules_to_shim['app.utility.base_planning_svc'] = _make_mod(
        'app.utility.base_planning_svc', BasePlanningService=_BasePlanningService)

    # aiohttp / jinja shims
    def _template_decorator(name):
        def decorator(fn):
            return fn
        return decorator
    modules_to_shim['aiohttp_jinja2'] = _make_mod('aiohttp_jinja2', template=_template_decorator)

    # 'plugins' package hierarchy for requirement imports
    modules_to_shim['plugins'] = _make_mod('plugins')
    modules_to_shim['plugins.stockpile'] = _make_mod('plugins.stockpile')
    modules_to_shim['plugins.stockpile.app'] = _make_mod('plugins.stockpile.app')
    modules_to_shim['plugins.stockpile.app.requirements'] = _make_mod('plugins.stockpile.app.requirements')

    for mod_name, mod in modules_to_shim.items():
        sys.modules.setdefault(mod_name, mod)


# Install shims once at import time of conftest
_install_caldera_shims()

# Now wire the base_requirement into the plugins namespace so that
# the concrete requirement modules can import it
import importlib
_br_spec = importlib.util.spec_from_file_location(
    'plugins.stockpile.app.requirements.base_requirement',
    '/tmp/stockpile-pytest/app/requirements/base_requirement.py',
)
_br_mod = importlib.util.module_from_spec(_br_spec)
_br_spec.loader.exec_module(_br_mod)
sys.modules['plugins.stockpile.app.requirements.base_requirement'] = _br_mod


# ---------------------------------------------------------------------------
# Reusable pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_fact():
    return FakeFact


@pytest.fixture
def fake_relationship():
    return FakeRelationship


@pytest.fixture
def fake_mapper():
    return FakeMapper


@pytest.fixture
def fake_link():
    return FakeLink


@pytest.fixture
def fake_operation():
    return FakeOperation


@pytest.fixture
def fake_agent():
    return FakeAgent


@pytest.fixture
def fake_ability():
    return FakeAbility


@pytest.fixture
def fake_executor():
    return FakeExecutor


@pytest.fixture
def parser_info():
    """Return a standard parser_info dict with one mapper and no used_facts."""
    def _make(source='test.source', target='test.target', edge='has',
              custom_parser_vals=None, used_facts=None, source_facts=None):
        mapper = FakeMapper(source=source, target=target, edge=edge,
                            custom_parser_vals=custom_parser_vals or {})
        return dict(
            mappers=[mapper],
            used_facts=used_facts or [],
            source_facts=source_facts or [],
        )
    return _make
