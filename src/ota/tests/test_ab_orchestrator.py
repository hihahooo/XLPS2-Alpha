"""A/B 双分区状态机与回滚编排（R5 双分区 / R7 健康确认与回滚）。"""
import pytest

from ota import config
from ota.ab_orchestrator import AbOrchestrator, DeviceAbState, UpgradePlan
from ota.exceptions import VersionMonotonicError


def _state(active="A", committed="A", current=100):
    return DeviceAbState(dev_id="DEV", active_slot=active, committed_slot=committed, current_version=current)


def test_plan_selects_nonactive_slot_and_monotonic():
    orch = AbOrchestrator()
    st = _state(active="A", current=100)
    plan = orch.plan_upgrade(st, 101)
    assert isinstance(plan, UpgradePlan)
    assert plan.target_slot == "B"  # 非活跃分区
    assert plan.target_version == 101


def test_plan_rejects_non_monotonic():
    orch = AbOrchestrator()
    with pytest.raises(VersionMonotonicError):
        orch.plan_upgrade(_state(current=100), 100)  # 平级
    with pytest.raises(VersionMonotonicError):
        orch.plan_upgrade(_state(current=100), 50)   # 降级


def test_start_command_payload():
    orch = AbOrchestrator()
    plan = orch.plan_upgrade(_state(current=100), 101)
    act = orch.start_command(plan)
    assert act.cmd == config.OTA_CMD_START
    assert act.rel_topic == config.TOPIC_OTA_CMD
    assert act.payload == {"cmd": "start", "target_version": "101", "slot": "B"}


def test_enter_health_window_sets_pending():
    orch = AbOrchestrator()
    st = _state(active="A", current=100)
    plan = orch.plan_upgrade(st, 101)
    ns, action = orch.enter_health_window(st, plan, now=1000)
    assert ns.pending is True
    assert ns.pending_target == 101
    assert ns.health_deadline == 1300
    assert ns.ota_state == config.OTA_STATE_VERIFYING
    assert action is None


def test_health_report_commits():
    orch = AbOrchestrator()
    st = _state(active="A", current=100)
    plan = orch.plan_upgrade(st, 101)
    ns1, _ = orch.enter_health_window(st, plan, now=1000)
    ns2, action = orch.on_health_report(ns1, now=1100)
    assert ns2.active_slot == "B"          # 提交到新分区
    assert ns2.committed_slot == "B"
    assert ns2.current_version == 101
    assert ns2.pending is False
    assert action is not None
    assert action.cmd == config.OTA_CMD_CONFIRM
    assert action.payload["slot"] == "B"


def test_timeout_rollback():
    orch = AbOrchestrator()
    st = _state(active="A", current=100)
    plan = orch.plan_upgrade(st, 101)
    ns1, _ = orch.enter_health_window(st, plan, now=1000)
    ns2, action = orch.on_timeout(ns1, now=2000)
    assert ns2.active_slot == "A"          # 回到上一稳定分区
    assert ns2.committed_slot == "A"
    assert ns2.pending is False
    assert action.cmd == config.OTA_CMD_ROLLBACK
    assert action.payload["slot"] == "A"
    assert ns2.last_result == config.OTA_RESULT_ROLLBACK


def test_on_result_variants():
    orch = AbOrchestrator()
    st = _state(active="A", current=100)
    plan = orch.plan_upgrade(st, 101)
    ns1, _ = orch.enter_health_window(st, plan, now=1000)

    ok_state, _ = orch.on_result(ns1, config.OTA_RESULT_OK)
    assert ok_state.active_slot == "B"
    assert ok_state.ota_state == config.OTA_STATE_ACTIVE

    fail_state, _ = orch.on_result(ns1, config.OTA_RESULT_FAIL)
    assert fail_state.active_slot == "A"
    assert fail_state.ota_state == config.OTA_STATE_ROLLBACK

    rb_state, _ = orch.on_result(ns1, config.OTA_RESULT_ROLLBACK)
    assert rb_state.active_slot == "A"


def test_manual_rollback():
    orch = AbOrchestrator()
    st = _state(active="B", committed="A", current=101)
    ns, action = orch.manual_rollback(st)
    assert ns.active_slot == "A"
    assert action.cmd == config.OTA_CMD_ROLLBACK
