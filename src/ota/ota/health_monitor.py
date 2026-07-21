"""健康观测窗（HEALTH_WINDOW_S，ADR-005 / R7）。

设备切换至新分区后，须在 ``HEALTH_WINDOW_S`` 秒内上报健康；云端据此确认提交，
超时未确认则触发回滚编排。

本类仅负责计时与状态，不持有设备状态、不下发指令——指令由 ``AbOrchestrator`` 决策。
"""
from __future__ import annotations

import enum
from typing import Optional


class HealthStatus(enum.Enum):
    IDLE = "idle"            # 未开窗
    PENDING = "pending"      # 窗内等待健康回报
    CONFIRMED = "confirmed"  # 已收到健康回报，可提交
    EXPIRED = "expired"      # 窗已超时，未确认 → 触发回滚


class HealthWindow:
    def __init__(self, window_s: int = None) -> None:
        from . import config

        self.window_s = window_s if window_s is not None else config.HEALTH_WINDOW_S
        self._deadline: Optional[int] = None
        self._confirmed = False

    # -- 开窗 ----------------------------------------------------------
    def open(self, now: int) -> None:
        if now < 0:
            raise ValueError("now 不可为负")
        self._deadline = now + self.window_s
        self._confirmed = False

    # -- 健康回报 ------------------------------------------------------
    def report(self, now: int) -> bool:
        """记录健康回报。窗内返回 True（确认），超时返回 False（忽略）。"""
        if self._deadline is None:
            return False
        if now > self._deadline:
            return False
        self._confirmed = True
        return True

    # -- 状态查询 ------------------------------------------------------
    @property
    def status(self) -> HealthStatus:
        if self._deadline is None:
            return HealthStatus.IDLE
        if self._confirmed:
            return HealthStatus.CONFIRMED
        # 需要外部 now 才能判断是否超时；用 is_expired 显式判定
        return HealthStatus.PENDING

    def is_confirmed(self) -> bool:
        return self._confirmed

    def is_expired(self, now: int) -> bool:
        return self._deadline is not None and now > self._deadline

    def remaining(self, now: int) -> int:
        if self._deadline is None:
            return 0
        return max(0, self._deadline - now)

    def deadline(self) -> Optional[int]:
        return self._deadline

    # -- 复位 ----------------------------------------------------------
    def close(self) -> None:
        self._deadline = None
        self._confirmed = False
