"""A/B 双分区状态机与回滚编排（R5 双分区 / R7 健康确认与回滚）。

职责边界
--------
``AbOrchestrator`` 是**无状态决策引擎**：输入「当前设备 A/B 状态 + 事件」，输出
「新状态 + 需下发的指令(PendingAction)」。自身不持有任何可变状态，便于纯函数式
单测。可变状态由 ``OtaService`` 持有，健康观测窗计时由 ``HealthWindow`` 负责。

流程（ADR-005）
----------------
云端下发到**非活跃**分区 → 本地烧写校验 → 重启切换 → 健康窗(300s)内设备上报健康
→ 超时未确认则**自动回滚**到上一稳定分区。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from . import config
from .exceptions import SlotError, VersionMonotonicError
from .versioning import assert_monotonic, parse_version


@dataclass
class DeviceAbState:
    """设备 A/B 视图（云端视角，非设备内部 FLAG）。"""

    dev_id: str
    active_slot: str = config.SLOT_A
    committed_slot: str = config.SLOT_A
    current_version: int = 0
    pending: bool = False
    pending_target: Optional[int] = None
    health_deadline: int = 0
    ota_state: str = config.OTA_STATE_IDLE
    last_result: Optional[str] = None

    def clone(self) -> "DeviceAbState":
        return copy.copy(self)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dev_id": self.dev_id,
            "active_slot": self.active_slot,
            "committed_slot": self.committed_slot,
            "current_version": self.current_version,
            "pending": self.pending,
            "pending_target": self.pending_target,
            "health_deadline": self.health_deadline,
            "ota_state": self.ota_state,
            "last_result": self.last_result,
        }


@dataclass(frozen=True)
class UpgradePlan:
    target_version: int
    target_slot: str


@dataclass(frozen=True)
class PendingAction:
    """需要云端下发的指令。"""

    cmd: str
    rel_topic: str
    payload: Dict[str, Any]


class AbOrchestrator:
    """A/B 决策引擎（无状态）。"""

    # -- 升级规划（R4 版本单调 + R5 非活跃分区）-----------------------
    def plan_upgrade(self, state: DeviceAbState, target_version: Any) -> UpgradePlan:
        """规划升级：校验版本单调（R4），选定**非活跃**分区（R5）。

        不修改 state；返回计划。违反单调抛 ``VersionMonotonicError``。
        """
        assert_monotonic(target_version, state.current_version)  # R4
        target_slot = config.other_slot(state.active_slot)        # R5
        return UpgradePlan(target_version=parse_version(target_version), target_slot=target_slot)

    # -- 下发「开始」指令 ------------------------------------------
    def start_command(self, plan: UpgradePlan) -> PendingAction:
        return PendingAction(
            cmd=config.OTA_CMD_START,
            rel_topic=config.TOPIC_OTA_CMD,
            payload={
                "cmd": config.OTA_CMD_START,
                "target_version": str(plan.target_version),
                "slot": plan.target_slot,
            },
        )

    # -- 设备进入新分区、等待健康确认（R7 健康窗开启）----------------
    def enter_health_window(
        self, state: DeviceAbState, plan: UpgradePlan, now: int
    ) -> Tuple[DeviceAbState, Optional[PendingAction]]:
        """设备已烧写校验并重启进新分区：标记 pending、设健康截止。

        返回（新状态, None）。实际 commit 指令在收到健康回报后由 on_health_report 下发。
        """
        ns = state.clone()
        ns.pending = True
        ns.pending_target = plan.target_version
        ns.health_deadline = now + config.HEALTH_WINDOW_S
        ns.ota_state = config.OTA_STATE_VERIFYING
        return ns, None

    # -- 健康确认：设备在窗内上报健康 → 提交（R7）-------------------
    def on_health_report(
        self, state: DeviceAbState, now: int
    ) -> Tuple[DeviceAbState, Optional[PendingAction]]:
        if not state.pending or state.pending_target is None:
            return state.clone(), None
        if state.health_deadline and now > state.health_deadline:
            # 已超时，不应再确认（由 on_timeout 处理）
            return state.clone(), None
        ns = state.clone()
        ns.active_slot = config.other_slot(ns.committed_slot)  # 新激活分区 = 旧的对偶
        ns.committed_slot = ns.active_slot
        ns.current_version = ns.pending_target
        ns.pending = False
        ns.pending_target = None
        ns.health_deadline = 0
        ns.ota_state = config.OTA_STATE_ACTIVE
        ns.last_result = config.OTA_RESULT_OK
        # 下发 confirm 让设备端固化 FLAG（若设备已自固化则幂等）
        action = PendingAction(
            cmd=config.OTA_CMD_CONFIRM,
            rel_topic=config.TOPIC_OTA_CMD,
            payload={"cmd": config.OTA_CMD_CONFIRM, "slot": ns.active_slot},
        )
        return ns, action

    # -- 健康窗超时：自动回滚到上一稳定分区（R7）--------------------
    def on_timeout(
        self, state: DeviceAbState, now: int
    ) -> Tuple[DeviceAbState, PendingAction]:
        """健康窗超时未确认 → 回滚：active 维持旧稳定分区，下发 rollback 指令。"""
        ns = state.clone()
        ns.active_slot = ns.committed_slot  # 回到上一稳定分区
        ns.pending = False
        ns.pending_target = None
        ns.health_deadline = 0
        ns.ota_state = config.OTA_STATE_ROLLBACK
        ns.last_result = config.OTA_RESULT_ROLLBACK
        action = PendingAction(
            cmd=config.OTA_CMD_ROLLBACK,
            rel_topic=config.TOPIC_OTA_CMD,
            payload={"cmd": config.OTA_CMD_ROLLBACK, "slot": ns.committed_slot},
        )
        return ns, action

    # -- 设备回报最终结果（ota/result）-----------------------------
    def on_result(
        self, state: DeviceAbState, result: str
    ) -> Tuple[DeviceAbState, Optional[PendingAction]]:
        if result not in config.OTA_RESULTS:
            raise ValueError(f"非法 ota_result: {result!r}")
        ns = state.clone()
        ns.last_result = result
        if result == config.OTA_RESULT_OK:
            if ns.pending_target is not None:
                ns.active_slot = config.other_slot(ns.committed_slot)
                ns.committed_slot = ns.active_slot
                ns.current_version = ns.pending_target
            ns.pending = False
            ns.pending_target = None
            ns.health_deadline = 0
            ns.ota_state = config.OTA_STATE_ACTIVE
        elif result in (config.OTA_RESULT_FAIL, config.OTA_RESULT_ROLLBACK):
            # 失败 / 回滚：回到上一稳定分区
            ns.active_slot = ns.committed_slot
            ns.pending = False
            ns.pending_target = None
            ns.health_deadline = 0
            ns.ota_state = config.OTA_STATE_ROLLBACK
        return ns, None

    # -- 用户/运维显式回滚（持有当前视图时）------------------------
    def manual_rollback(self, state: DeviceAbState) -> Tuple[DeviceAbState, PendingAction]:
        ns = state.clone()
        ns.active_slot = ns.committed_slot
        ns.pending = False
        ns.pending_target = None
        ns.health_deadline = 0
        ns.ota_state = config.OTA_STATE_ROLLBACK
        ns.last_result = config.OTA_RESULT_ROLLBACK
        action = PendingAction(
            cmd=config.OTA_CMD_ROLLBACK,
            rel_topic=config.TOPIC_OTA_CMD,
            payload={"cmd": config.OTA_CMD_ROLLBACK, "slot": ns.committed_slot},
        )
        return ns, action
