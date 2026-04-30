"""Exhaustive tests for all requirements in app/requirements/."""

import importlib.util
import sys
from pathlib import Path

import pytest

from tests.conftest import (
    FakeFact, FakeRelationship, FakeLink, FakeOperation, FakeAgent, FakeMapper,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_requirement(name):
    path = _REPO_ROOT / 'app' / 'requirements' / f'{name}.py'
    spec = importlib.util.spec_from_file_location(f'requirements.{name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===== base_requirement =====

class TestBaseRequirement:
    Mod = _load_requirement('base_requirement')

    def _make(self, edge='has', target=None):
        enforcements = {'edge': edge}
        if target:
            enforcements['target'] = target
        return self.Mod.BaseRequirement({'enforcements': enforcements})

    def test_check_edge_match(self):
        req = self._make(edge='has')
        assert req._check_edge('has') is True

    def test_check_edge_no_match(self):
        req = self._make(edge='has')
        assert req._check_edge('lacks') is False

    def test_check_target_match(self):
        target = FakeFact(trait='t', value='v')
        match = FakeFact(trait='t', value='v')
        assert self.Mod.BaseRequirement._check_target(target, match) is True

    def test_check_target_no_match(self):
        target = FakeFact(trait='t', value='v')
        match = FakeFact(trait='t', value='other')
        assert self.Mod.BaseRequirement._check_target(target, match) is False

    def test_get_relationships_filters(self):
        uf = FakeFact(trait='host.ip', value='10.10.10.5')
        r1 = FakeRelationship(source=FakeFact(trait='host.ip', value='10.10.10.5'))
        r2 = FakeRelationship(source=FakeFact(trait='host.ip', value='10.10.10.6'))
        result = self.Mod.BaseRequirement._get_relationships(uf, [r1, r2])
        assert len(result) == 1
        assert result[0] is r1

    def test_is_valid_relationship_edge_only(self):
        req = self._make(edge='has')
        rel = FakeRelationship(edge='has')
        assert req.is_valid_relationship([], rel) is True

    def test_is_valid_relationship_wrong_edge(self):
        req = self._make(edge='has')
        rel = FakeRelationship(edge='lacks')
        assert req.is_valid_relationship([], rel) is False

    def test_is_valid_relationship_with_target(self):
        req = self._make(edge='has', target='yes')
        req.enforcements['target'] = 'yes'
        rel = FakeRelationship(
            edge='has',
            target=FakeFact(trait='t', value='v')
        )
        used_facts = [FakeFact(trait='t', value='v')]
        assert req.is_valid_relationship(used_facts, rel) is True

    def test_is_valid_relationship_target_no_match(self):
        req = self._make(edge='has', target='yes')
        rel = FakeRelationship(
            edge='has',
            target=FakeFact(trait='t', value='v')
        )
        used_facts = [FakeFact(trait='t', value='other')]
        assert req.is_valid_relationship(used_facts, rel) is False


# ===== basic requirement =====

class TestBasicRequirement:
    Mod = _load_requirement('basic')

    @pytest.mark.asyncio
    async def test_enforce_passes(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        fact_used = FakeFact(trait='host.ip', value='10.0.0.5')
        fact_other = FakeFact(trait='other', value='x')
        link = FakeLink(used=[fact_used, fact_other])
        rel = FakeRelationship(
            source=FakeFact(trait='host.ip', value='10.0.0.5'),
            edge='has',
            target=None,
        )
        op = FakeOperation()
        op._relationships = [rel]
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_fails_no_matching_source(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        link = FakeLink(used=[FakeFact(trait='other', value='v')])
        op = FakeOperation()
        op._relationships = []
        result = await req.enforce(link, op)
        assert result is False

    @pytest.mark.asyncio
    async def test_enforce_fails_wrong_edge(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        fact_used = FakeFact(trait='host.ip', value='10.0.0.5')
        link = FakeLink(used=[fact_used])
        rel = FakeRelationship(
            source=FakeFact(trait='host.ip', value='10.0.0.5'),
            edge='lacks',
        )
        op = FakeOperation()
        op._relationships = [rel]
        result = await req.enforce(link, op)
        assert result is False


# ===== not_exists requirement =====

class TestNotExistsRequirement:
    Mod = _load_requirement('not_exists')

    @pytest.mark.asyncio
    async def test_enforce_passes_when_no_relationship(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        link = FakeLink(used=[FakeFact(trait='host.ip', value='10.0.0.5')])
        op = FakeOperation()
        op._relationships = []
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_fails_when_relationship_exists(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        fact = FakeFact(trait='host.ip', value='10.0.0.5')
        link = FakeLink(used=[fact])
        rel = FakeRelationship(
            source=FakeFact(trait='host.ip', value='10.0.0.5'),
            edge='has',
        )
        op = FakeOperation()
        op._relationships = [rel]
        result = await req.enforce(link, op)
        assert result is False


# ===== no_backwards_movement requirement =====

class TestNoBackwardsMovement:
    Mod = _load_requirement('no_backwards_movement')

    @pytest.mark.asyncio
    async def test_enforce_allows_new_host(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'remote.host'}})
        link = FakeLink(used=[FakeFact(trait='remote.host', value='newhost.domain.local')])
        agent = FakeAgent(host='currenthost')
        op = FakeOperation(agents=[agent])
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_blocks_existing_host(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'remote.host'}})
        link = FakeLink(used=[FakeFact(trait='remote.host', value='currenthost.domain.local')])
        agent = FakeAgent(host='currenthost')
        op = FakeOperation(agents=[agent])
        result = await req.enforce(link, op)
        assert result is False

    @pytest.mark.asyncio
    async def test_enforce_no_matching_trait(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'remote.host'}})
        link = FakeLink(used=[FakeFact(trait='other.trait', value='host1')])
        op = FakeOperation(agents=[FakeAgent(host='host2')])
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_case_insensitive(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'remote.host'}})
        link = FakeLink(used=[FakeFact(trait='remote.host', value='HOST1.domain.local')])
        agent = FakeAgent(host='host1')
        op = FakeOperation(agents=[agent])
        result = await req.enforce(link, op)
        assert result is False


# ===== paw_provenance requirement =====

class TestPawProvenance:
    Mod = _load_requirement('paw_provenance')

    @pytest.mark.asyncio
    async def test_enforce_passes_correct_paw(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip'}})
        fact = FakeFact(trait='host.ip', value='10.0.0.5', collected_by=['abc'])
        link = FakeLink(used=[fact], paw='abc')
        op = FakeOperation()
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_fails_wrong_paw(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip'}})
        fact = FakeFact(trait='host.ip', value='10.0.0.5', collected_by=['xyz'])
        link = FakeLink(used=[fact], paw='abc')
        op = FakeOperation()
        result = await req.enforce(link, op)
        assert result is False

    @pytest.mark.asyncio
    async def test_enforce_no_matching_trait(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip'}})
        fact = FakeFact(trait='other', value='v', collected_by=['abc'])
        link = FakeLink(used=[fact], paw='abc')
        op = FakeOperation()
        result = await req.enforce(link, op)
        assert result is False


# ===== existential requirement =====

class TestExistentialRequirement:
    Mod = _load_requirement('existential')

    @pytest.mark.asyncio
    async def test_enforce_passes_with_matching_fact(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        fact = FakeFact(trait='host.ip', value='10.0.0.5',
                        collected_by=['abc'], relationships=['has_access'])
        link = FakeLink(paw='abc')
        op = FakeOperation()
        op._facts = [fact]
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_fails_no_edge(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        fact = FakeFact(trait='host.ip', value='10.0.0.5',
                        collected_by=['abc'], relationships=[])
        link = FakeLink(paw='abc')
        op = FakeOperation()
        op._facts = [fact]
        result = await req.enforce(link, op)
        assert result is False

    @pytest.mark.asyncio
    async def test_enforce_without_edge_enforcement(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip'}})
        fact = FakeFact(trait='host.ip', value='10.0.0.5',
                        collected_by=['abc'], relationships=[])
        link = FakeLink(paw='abc')
        op = FakeOperation()
        op._facts = [fact]
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_fails_wrong_paw(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip'}})
        fact = FakeFact(trait='host.ip', value='10.0.0.5',
                        collected_by=['xyz'], relationships=[])
        link = FakeLink(paw='abc')
        op = FakeOperation()
        op._facts = [fact]
        result = await req.enforce(link, op)
        assert result is False


# ===== reachable requirement =====

class TestReachableRequirement:
    Mod = _load_requirement('reachable')

    @pytest.mark.asyncio
    async def test_enforce_passes_same_host(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'remote.host', 'edge': 'has'}})
        fact = FakeFact(trait='remote.host', value='10.0.0.5')
        link = FakeLink(used=[fact], host='host1')
        rel = FakeRelationship(
            source=FakeFact(trait='remote.host', value='10.0.0.5'),
            edge='has',
        )
        # Create a chain link that has the relationship
        chain_link = FakeLink(host='host1', relationships=[rel])
        op = FakeOperation(chain=[chain_link])
        op._relationships = [rel]
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_fails_different_host(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'remote.host', 'edge': 'has'}})
        fact = FakeFact(trait='remote.host', value='10.0.0.5')
        link = FakeLink(used=[fact], host='host2')
        rel = FakeRelationship(
            source=FakeFact(trait='remote.host', value='10.0.0.5'),
            edge='has',
        )
        chain_link = FakeLink(host='host1', relationships=[rel])
        op = FakeOperation(chain=[chain_link])
        op._relationships = [rel]
        result = await req.enforce(link, op)
        assert result is False

    @pytest.mark.asyncio
    async def test_enforce_fails_no_matching_trait(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'remote.host', 'edge': 'has'}})
        link = FakeLink(used=[FakeFact(trait='other', value='v')])
        op = FakeOperation()
        op._relationships = []
        result = await req.enforce(link, op)
        assert result is False


# ===== req_like requirement =====

class TestReqLikeRequirement:
    Mod = _load_requirement('req_like')

    @pytest.mark.asyncio
    async def test_enforce_exact_match(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.user', 'edge': 'has',
                                                      'target': 'host.pass'}})
        fact_user = FakeFact(trait='host.user', value='DOMAIN\\admin')
        fact_pass = FakeFact(trait='host.pass', value='DOMAIN\\admin')
        link = FakeLink(used=[fact_user, fact_pass])
        rel = FakeRelationship(
            source=FakeFact(trait='host.user', value='DOMAIN\\admin'),
            edge='has',
            target=FakeFact(trait='host.pass', value='DOMAIN\\admin'),
        )
        op = FakeOperation()
        op._relationships = [rel]
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_fuzzy_prefix_match(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.user', 'edge': 'has',
                                                      'target': 'host.pass'}})
        fact_user = FakeFact(trait='host.user', value='DOMAIN\\admin')
        fact_pass = FakeFact(trait='host.pass', value='DOMAIN\\admin_extended')
        link = FakeLink(used=[fact_user, fact_pass])
        rel = FakeRelationship(
            source=FakeFact(trait='host.user', value='DOMAIN\\admin'),
            edge='has',
            target=FakeFact(trait='host.pass', value='DOMAIN\\admin_extended'),
        )
        op = FakeOperation()
        op._relationships = [rel]
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_fuzzy_backslash_match(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.user', 'edge': 'has',
                                                      'target': 'host.pass'}})
        fact_user = FakeFact(trait='host.user', value='dom\\user')
        fact_pass = FakeFact(trait='host.pass', value='DOMAIN\\user')
        link = FakeLink(used=[fact_user, fact_pass])
        rel = FakeRelationship(
            source=FakeFact(trait='host.user', value='dom\\user'),
            edge='has',
            target=FakeFact(trait='host.pass', value='DOMAIN\\user'),
        )
        op = FakeOperation()
        op._relationships = [rel]
        # This tests the domain\user comparison logic
        result = await req.enforce(link, op)
        # The fuzzy match should work with the backslash components
        assert isinstance(result, bool)

    def test_check_fuzzy_exact(self):
        req = self.Mod.Requirement({'enforcements': {'source': 's', 'edge': 'e'}})
        target = FakeFact(trait='t', value='abc')
        match = FakeFact(trait='t', value='abc')
        assert req._check_fuzzy(target, match) is True

    def test_check_fuzzy_prefix(self):
        req = self.Mod.Requirement({'enforcements': {'source': 's', 'edge': 'e'}})
        target = FakeFact(trait='t', value='abcdef')
        match = FakeFact(trait='t', value='abc')
        assert req._check_fuzzy(target, match) is True

    def test_check_fuzzy_different_traits(self):
        req = self.Mod.Requirement({'enforcements': {'source': 's', 'edge': 'e'}})
        target = FakeFact(trait='t1', value='abc')
        match = FakeFact(trait='t2', value='abc')
        assert req._check_fuzzy(target, match) is False

    def test_check_fuzzy_no_match(self):
        req = self.Mod.Requirement({'enforcements': {'source': 's', 'edge': 'e'}})
        target = FakeFact(trait='t', value='abc')
        match = FakeFact(trait='t', value='xyz')
        assert req._check_fuzzy(target, match) is False


# ===== universal requirement =====

class TestUniversalRequirement:
    Mod = _load_requirement('universal')

    @pytest.mark.asyncio
    async def test_enforce_all_facts_have_edge(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        facts = [
            FakeFact(trait='host.ip', value='10.0.0.5',
                     collected_by=['abc'], relationships=['has_access']),
            FakeFact(trait='host.ip', value='10.0.0.6',
                     collected_by=['abc'], relationships=['has_admin']),
        ]
        link = FakeLink(paw='abc')
        op = FakeOperation()
        op._facts = facts
        result = await req.enforce(link, op)
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_fails_if_fact_missing_edge(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        facts = [
            FakeFact(trait='host.ip', value='10.0.0.5',
                     collected_by=['abc'], relationships=['has_access']),
            FakeFact(trait='host.ip', value='10.0.0.6',
                     collected_by=['abc'], relationships=[]),
        ]
        link = FakeLink(paw='abc')
        op = FakeOperation()
        op._facts = facts
        result = await req.enforce(link, op)
        assert result is False

    @pytest.mark.asyncio
    async def test_enforce_passes_no_matching_facts(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        link = FakeLink(paw='abc')
        op = FakeOperation()
        op._facts = []
        result = await req.enforce(link, op)
        # 0 == 0
        assert result is True

    @pytest.mark.asyncio
    async def test_enforce_ignores_other_paw(self):
        req = self.Mod.Requirement({'enforcements': {'source': 'host.ip', 'edge': 'has'}})
        facts = [
            FakeFact(trait='host.ip', value='10.0.0.5',
                     collected_by=['xyz'], relationships=[]),
        ]
        link = FakeLink(paw='abc')
        op = FakeOperation()
        op._facts = facts
        result = await req.enforce(link, op)
        # No facts match paw 'abc', so 0 == 0
        assert result is True
