"""Exhaustive tests for all planners in app/planners/."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from tests.conftest import (
    FakeOperation, FakeLink, FakeAgent, FakeAbility, FakeExecutor,
    FakeFact, FakeAdversary, FakeGoal, FakeObjective, FakeParser, FakeParserConfig,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_planner(name):
    path = _REPO_ROOT / 'app' / 'planners' / f'{name}.py'
    spec = importlib.util.spec_from_file_location(f'planners.{name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===== batch planner =====

class TestBatchPlanner:
    Mod = _load_planner('batch')

    def test_init(self):
        op = FakeOperation()
        planning_svc = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        assert planner.state_machine == ['batch']
        assert planner.next_bucket == 'batch'
        assert planner.stopping_condition_met is False

    @pytest.mark.asyncio
    async def test_execute(self):
        op = FakeOperation()
        planning_svc = AsyncMock()
        planning_svc.execute_planner = AsyncMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        await planner.execute()
        planning_svc.execute_planner.assert_awaited_once_with(planner)

    @pytest.mark.asyncio
    async def test_batch_no_links(self):
        op = FakeOperation()
        planning_svc = AsyncMock()
        planning_svc.get_links = AsyncMock(return_value=[])
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        await planner.batch()
        assert planner.next_bucket is None

    @pytest.mark.asyncio
    async def test_batch_with_links(self):
        op = FakeOperation()
        link = FakeLink(id='link-1')
        call_count = [0]

        async def get_links_side_effect(operation):
            call_count[0] += 1
            if call_count[0] == 1:
                return [link]
            return []

        planning_svc = AsyncMock()
        planning_svc.get_links = get_links_side_effect
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        await planner.batch()
        assert planner.next_bucket is None
        assert len(op._applied) == 1

    def test_stopping_conditions(self):
        op = FakeOperation()
        planning_svc = MagicMock()
        conditions = [FakeFact(trait='stop', value='now')]
        planner = self.Mod.LogicalPlanner(op, planning_svc, stopping_conditions=conditions)
        assert len(planner.stopping_conditions) == 1


# ===== buckets planner =====

class TestBucketsPlanner:
    Mod = _load_planner('buckets')

    def test_init(self):
        op = FakeOperation()
        planning_svc = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        assert planner.next_bucket == 'initial_access'
        assert len(planner.state_machine) == 12
        assert planner.current_length == 0

    @pytest.mark.asyncio
    async def test_execute(self):
        op = FakeOperation()
        planning_svc = AsyncMock()
        planning_svc.execute_planner = AsyncMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        await planner.execute()
        planning_svc.execute_planner.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_initial_access(self):
        op = FakeOperation()
        planning_svc = AsyncMock()
        planning_svc.exhaust_bucket = AsyncMock()
        planning_svc.default_next_bucket = AsyncMock(return_value='defense_evasion')
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        await planner.initial_access()
        planning_svc.exhaust_bucket.assert_awaited_once_with(planner, 'initial-access', op)
        assert planner.next_bucket == 'defense_evasion'

    @pytest.mark.asyncio
    async def test_discovery(self):
        op = FakeOperation()
        planning_svc = AsyncMock()
        planning_svc.exhaust_bucket = AsyncMock()
        planning_svc.default_next_bucket = AsyncMock(return_value='execution')
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        await planner.discovery()
        planning_svc.exhaust_bucket.assert_awaited_once_with(planner, 'discovery', op)

    @pytest.mark.asyncio
    async def test_impact_no_progress_auto_close(self):
        op = FakeOperation(auto_close=True, chain=[])
        planning_svc = AsyncMock()
        planning_svc.exhaust_bucket = AsyncMock()
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        planner.current_length = 0
        await planner.impact()
        assert planner.next_bucket is None

    @pytest.mark.asyncio
    async def test_impact_progress_continues(self):
        link = FakeLink()
        op = FakeOperation(chain=[link])
        planning_svc = AsyncMock()
        planning_svc.exhaust_bucket = AsyncMock()
        planning_svc.default_next_bucket = AsyncMock(return_value='initial_access')
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        planner.current_length = 0
        await planner.impact()
        assert planner.current_length == 1
        assert planner.next_bucket == 'initial_access'

    @pytest.mark.asyncio
    async def test_all_bucket_methods_exist(self):
        op = FakeOperation()
        planning_svc = AsyncMock()
        planning_svc.exhaust_bucket = AsyncMock()
        planning_svc.default_next_bucket = AsyncMock(return_value=None)
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        for bucket in planner.state_machine:
            assert hasattr(planner, bucket)
            assert callable(getattr(planner, bucket))


# ===== bayes planner =====

class TestBayesPlanner:
    Mod = _load_planner('bayes')

    def _make_planner(self, **kwargs):
        op = kwargs.pop('operation', FakeOperation())
        planning_svc = kwargs.pop('planning_svc', MagicMock())
        planning_svc.log = MagicMock()
        return self.Mod.LogicalPlanner(
            operation=op,
            planning_svc=planning_svc,
            min_prob_link_success=kwargs.get('min_prob_link_success', 0.49),
            min_link_data=kwargs.get('min_link_data', 3),
            debug=kwargs.get('debug', False),
        )

    def test_init(self):
        planner = self._make_planner()
        assert planner.state_machine == ['bayes_state']
        assert planner.next_bucket == 'bayes_state'
        assert planner.links_executed == 0
        assert planner.matrix_past_links is None

    @pytest.mark.asyncio
    async def test_execute(self):
        planning_svc = AsyncMock()
        planning_svc.execute_planner = AsyncMock()
        planning_svc.log = MagicMock()
        planner = self._make_planner(planning_svc=planning_svc)
        await planner.execute()
        planning_svc.execute_planner.assert_awaited_once()

    def test_query_link_matrix_empty(self):
        planner = self._make_planner()
        result = planner._query_link_matrix([], {'Ability_ID': 'x'})
        assert result == []

    def test_query_link_matrix_match(self):
        planner = self._make_planner()
        # Build a row matching FEATURE_NAMES order
        from tests.conftest import FakeFact
        row = [
            'ab-1',  # Ability_ID
            'adv-1',  # Adversary_ID
            'Test',  # Adversary_Name
            'User',  # Agent_Privilege
            'http',  # Agent_Protocol
            'whoami',  # Command
            'psh',  # Executor_Name
            'windows',  # Executor_Platform
            'amd64',  # Host_Architecture
            {},  # Link_Facts
            0,  # Number_Facts
            'plain-text',  # Obfuscator
            'atomic',  # Planner
            0,  # Status
            True,  # Trusted_Status
            50,  # Visibility_Score
        ]
        result = planner._query_link_matrix([row], {'Ability_ID': 'ab-1'})
        assert len(result) == 1

    def test_query_link_matrix_no_match(self):
        planner = self._make_planner()
        row = ['ab-1'] + [''] * 15
        result = planner._query_link_matrix([row], {'Ability_ID': 'ab-2'})
        assert result == []

    def test_backup_atomic_ordering_empty(self):
        adversary = FakeAdversary(atomic_ordering=['ab-1', 'ab-2'])
        op = FakeOperation(adversary=adversary)
        planner = self._make_planner(operation=op)
        result = planner._backup_atomic_ordering([])
        assert result is None

    def test_backup_atomic_ordering_selects_first(self):
        adversary = FakeAdversary(atomic_ordering=['ab-1', 'ab-2'])
        op = FakeOperation(adversary=adversary)
        planner = self._make_planner(operation=op)
        link1 = FakeLink(ability=FakeAbility(ability_id='ab-2'))
        link2 = FakeLink(ability=FakeAbility(ability_id='ab-1'))
        result = planner._backup_atomic_ordering([link1, link2])
        assert result.ability.ability_id == 'ab-1'

    def test_get_useful_facts(self):
        planner = self._make_planner()
        link = FakeLink()
        fact1 = FakeFact(trait='host.ip', value='10.0.0.5')
        fact2 = FakeFact(trait='safe.trait', value='value')
        link.used = [fact1, fact2]
        result = planner._get_useful_facts(link)
        # host. prefix should be excluded
        assert 'host.ip' not in result
        assert 'safe.trait' in result

    def test_feature_names(self):
        assert len(self.Mod.FEATURE_NAMES) == 16

    def test_update_after_links_constant(self):
        assert self.Mod.UPDATE_AFTER_LINKS == 10


# ===== look_ahead planner =====

class TestLookAheadPlanner:
    Mod = _load_planner('look_ahead')

    def test_init_defaults(self):
        op = FakeOperation()
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        assert planner.depth == 3
        assert planner.discount == 0.9
        assert planner.default_reward == 1
        assert planner.state_machine == ['look_ahead']
        assert planner.next_bucket == 'look_ahead'

    def test_init_custom(self):
        op = FakeOperation()
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planner = self.Mod.LogicalPlanner(
            op, planning_svc, depth=5, discount=0.8,
            default_reward=2, ability_rewards={'ab-1': 10}
        )
        assert planner.depth == 5
        assert planner.discount == 0.8
        assert planner.default_reward == 2
        assert planner.ability_rewards == {'ab-1': 10}

    @pytest.mark.asyncio
    async def test_execute(self):
        op = FakeOperation()
        planning_svc = AsyncMock()
        planning_svc.execute_planner = AsyncMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        await planner.execute()
        planning_svc.execute_planner.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_future_reward_base_case(self):
        op = FakeOperation()
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planner = self.Mod.LogicalPlanner(op, planning_svc, depth=1)
        agent = FakeAgent()
        ability = FakeAbility(ability_id='ab-1')
        executor = FakeExecutor(parsers=[], command='test')
        ability._executor = executor
        # Depth > self.depth should return 0
        reward = await planner._future_reward(agent, ability, set(), 5)
        assert reward == 0

    @pytest.mark.asyncio
    async def test_future_reward_with_reward(self):
        op = FakeOperation()
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planner = self.Mod.LogicalPlanner(op, planning_svc, depth=1, default_reward=10)
        agent = FakeAgent()
        ability = FakeAbility(ability_id='ab-1')
        executor = FakeExecutor(parsers=[], command='test')
        ability._executor = executor
        reward = await planner._future_reward(agent, ability, set(), 0)
        # reward = 10 * 0.9^0 + 0 = 10
        assert reward == 10.0

    @pytest.mark.asyncio
    async def test_abilities_that_follow_empty(self):
        op = FakeOperation()
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        agent = FakeAgent()
        ability = FakeAbility(ability_id='ab-1')
        executor = FakeExecutor(parsers=[], command='test')
        ability._executor = executor
        result = await planner._abilities_that_follow(agent, ability, set())
        assert result == []

    @pytest.mark.asyncio
    async def test_abilities_that_follow_with_match(self):
        op = FakeOperation()
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        agent = FakeAgent()

        cfg = FakeParserConfig(source='host.ip', target='host.name')
        parser = FakeParser(parserconfigs=[cfg])
        exec1 = FakeExecutor(parsers=[parser], command='cmd1')
        ability1 = FakeAbility(ability_id='ab-1', _executor=exec1)

        exec2 = FakeExecutor(parsers=[], command='use #{host.ip} to connect')
        ability2 = FakeAbility(ability_id='ab-2', _executor=exec2)

        result = await planner._abilities_that_follow(agent, ability1, {ability2})
        assert len(result) == 1
        assert result[0].ability_id == 'ab-2'

    @pytest.mark.asyncio
    async def test_look_ahead_no_agents(self):
        op = FakeOperation(agents=[])
        planning_svc = AsyncMock()
        planning_svc.get_service = MagicMock(return_value=AsyncMock())
        planning_svc.execute_planner = AsyncMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        op.adversary = FakeAdversary(atomic_ordering=[])
        await planner.look_ahead()
        assert planner.next_bucket is None


# ===== guided planner (basic structural tests) =====

class TestGuidedPlanner:
    Mod = _load_planner('guided')

    def test_init(self):
        objective = FakeObjective(goals=[FakeGoal(target='host.ip')])
        adversary = FakeAdversary(atomic_ordering=['ab-1'])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        assert planner.state_machine == ['guided']
        assert planner.next_bucket == 'guided'
        assert planner.half_life_penalty == self.Mod.DEFAULT_HALF_LIFE_PENALTY
        assert planner.half_life_gain == self.Mod.DEFAULT_HALF_LIFE_GAIN

    @pytest.mark.asyncio
    async def test_execute(self):
        objective = FakeObjective(goals=[])
        adversary = FakeAdversary(atomic_ordering=[])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = AsyncMock()
        planning_svc.execute_planner = AsyncMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        await planner.execute()
        planning_svc.execute_planner.assert_awaited_once()

    def test_calculate_goal_action_penalty(self):
        objective = FakeObjective(goals=[])
        adversary = FakeAdversary(atomic_ordering=[])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc, goal_action_decay=2)
        result = planner._calculate_goal_action_penalty(max_value=5.0, effective_score=5.0)
        expected = 5.0 - 1 + float(5.0 + 1 - 5.0) / 2
        assert result == expected

    def test_calculate_non_goal_action_penalty_closer(self):
        objective = FakeObjective(goals=[])
        adversary = FakeAdversary(atomic_ordering=[])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        # max_value > abs(absolute_score) => reset to absolute
        result = planner._calculate_non_goal_action_penalty(
            max_value=5.0, absolute_score=3.0, effective_score=2.0)
        assert result == 3.0

    def test_calculate_non_goal_action_penalty_not_closer(self):
        objective = FakeObjective(goals=[])
        adversary = FakeAdversary(atomic_ordering=[])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc, half_life_penalty=4)
        result = planner._calculate_non_goal_action_penalty(
            max_value=3.0, absolute_score=5.0, effective_score=4.0)
        assert result == 4.0 / 4

    def test_apply_effective_distance_penalty_goal_action(self):
        objective = FakeObjective(goals=[])
        adversary = FakeAdversary(atomic_ordering=[])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        planner.last_action = FakeAbility(ability_id='ab-1')
        planner.goal_actions = {'ab-1'}
        result = planner._apply_effective_distance_penalty(5.0, 5.0, 5.0)
        assert isinstance(result, float)

    def test_apply_effective_distance_penalty_non_goal_action(self):
        objective = FakeObjective(goals=[])
        adversary = FakeAdversary(atomic_ordering=[])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        planner.last_action = FakeAbility(ability_id='ab-1')
        planner.goal_actions = set()
        result = planner._apply_effective_distance_penalty(5.0, 3.0, 5.0)
        assert isinstance(result, float)

    def test_is_invalid_executor_none(self):
        objective = FakeObjective(goals=[])
        adversary = FakeAdversary(atomic_ordering=[])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        assert planner._is_invalid_executor(None) is True

    def test_is_invalid_executor_no_command(self):
        objective = FakeObjective(goals=[])
        adversary = FakeAdversary(atomic_ordering=[])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        executor = FakeExecutor(command=None)
        assert planner._is_invalid_executor(executor) is True

    def test_is_invalid_executor_valid(self):
        objective = FakeObjective(goals=[])
        adversary = FakeAdversary(atomic_ordering=[])
        op = FakeOperation(objective=objective, adversary=adversary)
        planning_svc = MagicMock()
        planning_svc.get_service = MagicMock(return_value=MagicMock())
        planning_svc.log = MagicMock()
        planner = self.Mod.LogicalPlanner(op, planning_svc)
        executor = FakeExecutor(command='whoami')
        assert planner._is_invalid_executor(executor) is False

    def test_default_constants(self):
        assert self.Mod.DEFAULT_HALF_LIFE_PENALTY == 4
        assert self.Mod.DEFAULT_HALF_LIFE_GAIN == 2
        assert self.Mod.DEFAULT_GOAL_ACTION_DECAY == 2
        assert self.Mod.DEFAULT_GOAL_WEIGHT == 1
        assert self.Mod.DEFAULT_FACT_SCORE_WEIGHT == 0
        assert self.Mod.DEFAULT_EXHAUSTION_GOAL_COUNT == 1
