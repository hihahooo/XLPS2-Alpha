"""OTA 服务：编排 cmd / data / progress / result 全流程。

职责
----
- 升级前：版本单调校验（R4）+ 选非活跃分区（R5）→ 下发 ota/cmd(start)。
- 下发：分片（CHUNK_SIZE，seq+CRC）经 ota/data；依设备进度 last_seq 断点续传（R-断电续传）。
- 激活：设备烧写校验后重启进新分区 → 开启健康观测窗（HEALTH_WINDOW_S）。
- 健康确认（R7）：窗内收到健康回报 → 下发 confirm 提交；超时未确认 → 自动回滚（rollback）。
- 异常隔离（R15）：所有入口过 schema 校验；单设备/单包异常不拖垮服务。

云端持有可变状态（每设备 A/B 视图、每任务健康窗）；决策交给 ``AbOrchestrator``
与 ``HealthWindow``，保持纯函数可测。
"""
from __future__ import annotations

import enum
import json
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from . import config
from . import chunking as ck
from .ab_orchestrator import AbOrchestrator, DeviceAbState, PendingAction
from .exceptions import OtaError, SchemaError, VersionMonotonicError
from .health_monitor import HealthWindow
from .schema import (
    validate_ota_cmd,
    validate_ota_data,
    validate_ota_progress,
    validate_ota_result,
    CURRENT_STATE_SENTINEL,
)
from .store import FirmwareMeta, FirmwareStore
from .topics import build_topic, parse_topic
from .versioning import parse_version


class OtaJobStatus(enum.Enum):
    PLANNED = "planned"
    STREAMING = "streaming"
    WAITING_HEALTH = "waiting_health"
    CONFIRMED = "confirmed"
    DONE = "done"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class OtaJob:
    dev_id: str
    target_version: int
    target_slot: str
    ftype: int
    total_chunks: int
    package_blob: bytes = b""
    received_seqs: Set[int] = field(default_factory=set)
    status: OtaJobStatus = OtaJobStatus.PLANNED
    health: HealthWindow = field(default_factory=HealthWindow)
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


# 事件回调签名 (dev_id, event_type, payload) -> None
EventListener = Callable[[str, str, Dict[str, Any]], None]


class OtaService:
    def __init__(
        self,
        transport,
        store: FirmwareStore,
        signing_key: bytes,
        orchestrator: Optional[AbOrchestrator] = None,
        now_provider: Callable[[], float] = time.time,
        on_event: Optional[EventListener] = None,
    ) -> None:
        self.transport = transport
        self.store = store
        self.key = signing_key
        self.orch = orchestrator or AbOrchestrator()
        self._now = now_provider
        self._on_event = on_event
        self._devices: Dict[str, DeviceAbState] = {}
        self._jobs: Dict[str, OtaJob] = {}
        self._started = False

    # -- 生命周期 --------------------------------------------------------
    def start(self) -> None:
        self.transport.subscribe("rgv/+/ota/progress", self._on_progress, qos=1)
        self.transport.subscribe("rgv/+/ota/result", self._on_result, qos=1)
        self.transport.subscribe("rgv/+/telemetry", self._on_telemetry, qos=1)
        self.transport.start()
        self._started = True

    def stop(self) -> None:
        self.transport.stop()
        self._started = False

    # -- 设备状态视图 ----------------------------------------------------
    def _device(self, dev_id: str) -> DeviceAbState:
        if dev_id not in self._devices:
            self._devices[dev_id] = DeviceAbState(dev_id=dev_id)
        return self._devices[dev_id]

    def device_view(self, dev_id: str) -> DeviceAbState:
        return self._device(dev_id).clone()

    def get_job(self, dev_id: str) -> Optional[OtaJob]:
        return self._jobs.get(dev_id)

    def list_jobs(self) -> List[OtaJob]:
        return list(self._jobs.values())

    # -- 事件 ------------------------------------------------------------
    def _emit(self, dev_id: str, etype: str, data: Dict[str, Any]) -> None:
        if self._on_event:
            try:
                self._on_event(dev_id, etype, data)
            except Exception:  # 异常隔离：监听器故障不影响主流程
                traceback.print_exc()

    # -- 升级提交（R4 + R5）-------------------------------------------
    def submit_upgrade(
        self,
        dev_id: str,
        version: Any,
        ftype: int = config.FW_TYPE_FIRMWARE,
        package_blob: Optional[bytes] = None,
    ) -> OtaJob:
        """提交一次升级：版本单调校验 + 选非活跃分区 + 下发 start + 流式分发。"""
        # 取包（版本单调在仓库 publish 与 plan_upgrade 双重校验）
        blob = package_blob
        if blob is None:
            blob = self.store.get_blob(version)
        ver = parse_version(version)

        state = self._device(dev_id)
        plan = self.orch.plan_upgrade(state, ver)  # 抛 VersionMonotonicError (R4)
        action = self.orch.start_command(plan)
        self._publish_cmd(dev_id, action)

        chunks = ck.chunk_package(blob, config.CHUNK_SIZE)
        job = OtaJob(
            dev_id=dev_id,
            target_version=plan.target_version,
            target_slot=plan.target_slot,
            ftype=ftype,
            total_chunks=len(chunks),
            package_blob=blob,
            status=OtaJobStatus.STREAMING,
        )
        self._jobs[dev_id] = job
        self._emit(dev_id, "upgrade_submitted", {
            "target_version": plan.target_version,
            "target_slot": plan.target_slot,
            "total_chunks": len(chunks),
        })
        # 首轮全量分发（断线后续由进度 last_seq 续传）
        self._stream_chunks(dev_id, job, set(range(len(chunks))))
        return job

    # -- 指令下发 --------------------------------------------------------
    def _publish_cmd(self, dev_id: str, action: PendingAction) -> None:
        validate_ota_cmd(action.payload)  # 不绕过 schema
        topic = build_topic(dev_id, action.rel_topic)
        self.transport.publish(topic, json.dumps(action.payload, separators=(",", ":")).encode("utf-8"), qos=1)

    # -- 分片分发（R-断电续传）----------------------------------------
    def _stream_chunks(self, dev_id: str, job: OtaJob, seqs: Set[int]) -> None:
        if not seqs:
            return
        all_chunks = ck.chunk_package(job.package_blob, config.CHUNK_SIZE)
        send = [c for c in all_chunks if c.seq in seqs]
        if not send:
            return
        payload = ck.chunks_to_payload(send, total=job.total_chunks, ftype=job.ftype, version=job.target_version)
        validate_ota_data(json.loads(payload.decode("utf-8")))  # 不绕过 schema
        topic = build_topic(dev_id, config.TOPIC_OTA_DATA)
        self.transport.publish(topic, payload, qos=1)
        job.received_seqs.update(c.seq for c in send)

    # -- 进度回报（device→cloud）---------------------------------------
    def _on_progress(self, topic: str, payload: bytes) -> None:
        try:
            dev_id, _ = parse_topic(topic)
            msg = json.loads(payload.decode("utf-8"))
            validate_ota_progress(msg)
        except (SchemaError, ValueError) as e:
            traceback.print_exc()
            return  # 异常隔离：单条非法消息不中断服务

        job = self._jobs.get(dev_id)
        state = self._device(dev_id)
        now = int(self._now())

        if "ota_state" in msg:
            state.ota_state = msg["ota_state"]
        if "ota_progress_pct" in msg:
            pass  # 仅记录，可扩展

        # 续传：设备上报已连续收到的最高 seq
        if msg.get("ota_state") == config.OTA_STATE_DOWNLOADING and "last_seq" in msg:
            last = int(msg["last_seq"])
            missing = set(ck.resume_plan(job.total_chunks, range(0, last + 1))) if job else set()
            if missing:
                self._stream_chunks(dev_id, job, missing)
            return

        # 设备进新分区：开启健康窗（R7）
        if msg.get("ota_state") in (config.OTA_STATE_VERIFYING, config.OTA_STATE_ACTIVE) and job is not None:
            if job.status == OtaJobStatus.STREAMING or job.status == OtaJobStatus.WAITING_HEALTH:
                if not job.health.deadline():
                    ns, _ = self.orch.enter_health_window(
                        state, _plan_from_job(job), now
                    )
                    self._devices[dev_id] = ns
                    job.health.open(now)
                    job.status = OtaJobStatus.WAITING_HEALTH
                    self._emit(dev_id, "health_window_open", {"deadline": job.health.deadline()})
                # 收到 active（健康）= 健康回报 → 确认
                if msg.get("ota_state") == config.OTA_STATE_ACTIVE:
                    self._confirm(dev_id, job)

    # -- 健康确认（R7）--------------------------------------------------
    def _confirm(self, dev_id: str, job: OtaJob) -> None:
        now = int(self._now())
        if job.health.is_expired(now):
            return  # 已超时，交给 tick 处理回滚
        if not job.health.report(now):
            return
        state = self._device(dev_id)
        ns, action = self.orch.on_health_report(state, now)
        self._devices[dev_id] = ns
        if action:
            self._publish_cmd(dev_id, action)
        job.status = OtaJobStatus.CONFIRMED
        self._emit(dev_id, "health_confirmed", {"active_slot": ns.active_slot, "version": ns.current_version})

    # -- 遥测（device→cloud）：可作为健康回报来源之一 -------------------
    def _on_telemetry(self, topic: str, payload: bytes) -> None:
        try:
            dev_id, _ = parse_topic(topic)
            msg = json.loads(payload.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return
        job = self._jobs.get(dev_id)
        if not job or job.status != OtaJobStatus.WAITING_HEALTH:
            return
        # 健康判据（ADR-003：current_state 为 uint16，0xFFFF=未初始化）：
        # is_safe=true 或 fault_level==0 视为健康；current_state 为合法 uint16
        # 且非哨兵时亦视为设备存活上报（可确认）。
        cs = msg.get("current_state")
        healthy = (
            (msg.get("is_safe") is True)
            or (msg.get("fault_level") == 0)
            or (isinstance(cs, int) and cs != CURRENT_STATE_SENTINEL)
        )
        if healthy:
            self._confirm(dev_id, job)

    # -- 结果回报（device→cloud）---------------------------------------
    def _on_result(self, topic: str, payload: bytes) -> None:
        try:
            dev_id, _ = parse_topic(topic)
            msg = json.loads(payload.decode("utf-8"))
            validate_ota_result(msg)
        except (SchemaError, ValueError) as e:
            traceback.print_exc()
            return

        result = msg["ota_result"]
        job = self._jobs.get(dev_id)
        state = self._device(dev_id)
        ns, _ = self.orch.on_result(state, result)
        self._devices[dev_id] = ns
        if job:
            job.health.close()
            if result == config.OTA_RESULT_OK:
                job.status = OtaJobStatus.DONE
            elif result == config.OTA_RESULT_FAIL:
                job.status = OtaJobStatus.FAILED
            else:  # rollback
                job.status = OtaJobStatus.ROLLED_BACK
            job.finished_at = self._now()
        self._emit(dev_id, "result", {"ota_result": result, "active_slot": ns.active_slot})

    # -- 超时轮询（R7 自动回滚）--------------------------------------
    def tick(self, now: Optional[float] = None) -> List[str]:
        """检查所有处于健康窗的任务；超时未确认则触发回滚编排。返回已回滚的 dev_id 列表。"""
        now = int(now if now is not None else self._now())
        rolled: List[str] = []
        for dev_id, job in list(self._jobs.items()):
            if job.status != OtaJobStatus.WAITING_HEALTH:
                continue
            if job.health.is_expired(now):
                state = self._device(dev_id)
                ns, action = self.orch.on_timeout(state, now)
                self._devices[dev_id] = ns
                self._publish_cmd(dev_id, action)
                job.health.close()
                job.status = OtaJobStatus.ROLLED_BACK
                job.finished_at = now
                rolled.append(dev_id)
                self._emit(dev_id, "health_timeout_rollback", {"active_slot": ns.active_slot})
        return rolled

    # -- 显式回滚（运维）---------------------------------------------
    def request_rollback(self, dev_id: str) -> None:
        state = self._device(dev_id)
        ns, action = self.orch.manual_rollback(state)
        self._devices[dev_id] = ns
        self._publish_cmd(dev_id, action)
        job = self._jobs.get(dev_id)
        if job:
            job.health.close()
            job.status = OtaJobStatus.ROLLED_BACK


def _plan_from_job(job: OtaJob):
    """由 Job 还原 UpgradePlan（供 enter_health_window 使用）。"""
    from .ab_orchestrator import UpgradePlan

    return UpgradePlan(target_version=job.target_version, target_slot=job.target_slot)
