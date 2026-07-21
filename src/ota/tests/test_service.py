"""OTA 服务端到端集成测试（InMemoryTransport + 模拟设备，无需 broker）。

覆盖 P1 五规则：版本单调(R4) / A/B 双分区(R5) / 断点续传 / 健康确认(R7) /
异常隔离(R15) + 服务级异常隔离（单条非法消息不中断）。
"""
import json

import pytest

from ota import config
from ota.exceptions import VersionMonotonicError
from ota.framing import pack_package
from ota.mqtt_adapter import InMemoryTransport
from ota.service import OtaJobStatus, OtaService
from ota.store import FirmwareStore
from ota.topics import build_topic


class Clock:
    def __init__(self, t: int = 1000):
        self.t = t

    def now(self):
        return self.t


class FakeDevice:
    """进程内模拟设备端 OTA 客户端（CFW L5 配置运维层）。"""

    def __init__(self, tr: InMemoryTransport, dev_id: str, clock: Clock):
        self.tr = tr
        self.dev = dev_id
        self.clock = clock
        self.buf = {}
        self.total = None
        self.target_slot = None
        self.target_version = None
        self.active = "A"
        self.committed = "A"
        self.cmds = []
        tr.on_cloud_message(f"rgv/{dev_id}/ota/cmd", self._on_cmd)
        tr.on_cloud_message(f"rgv/{dev_id}/ota/data", self._on_data)

    def _on_cmd(self, _topic, payload):
        msg = json.loads(payload)
        self.cmds.append(msg)
        if msg.get("cmd") == config.OTA_CMD_START:
            self.target_slot = msg["slot"]
            self.target_version = int(msg["target_version"])

    def _on_data(self, _topic, payload):
        obj = json.loads(payload)
        self.total = obj["total"]
        for c in obj["chunks"]:
            self.buf[c["seq"]] = c

    def finish_download(self, last_seq=None):
        ls = last_seq if last_seq is not None else (self.total - 1 if self.total else 0)
        self._pub(config.OTA_STATE_DOWNLOADING, last_seq=ls)

    def flash(self, state=config.OTA_STATE_ACTIVE):
        self.active = self.target_slot or "A"
        self._pub(state)

    def report_result(self, res):
        self.tr.device_publish(
            build_topic(self.dev, config.TOPIC_OTA_RESULT),
            json.dumps({"ota_result": res}).encode(),
        )

    def _pub(self, state, **kw):
        payload = {
            "ota_state": state,
            "ota_active_slot": self.active,
            "ota_progress_pct": 100,
            "ota_target_version": str(self.target_version),
            **kw,
        }
        self.tr.device_publish(
            build_topic(self.dev, config.TOPIC_OTA_PROGRESS),
            json.dumps(payload).encode(),
        )


def _make(key, tmp_path):
    tr = InMemoryTransport()
    tr.start()
    clock = Clock(1000)
    store = FirmwareStore(str(tmp_path), signing_key=key)
    svc = OtaService(tr, store, key, now_provider=clock.now)
    svc.start()
    return tr, clock, svc


def _blob(key, version, payload=b"FIRMWARE-IMAGE-DATA"):
    return pack_package(version, config.FW_TYPE_FIRMWARE, payload, key).blob


# ---- 1. 完整成功路径（R5 双分区 + R7 健康确认）------------------------
def test_full_success(key, tmp_path):
    tr, clock, svc = _make(key, tmp_path)
    dev = FakeDevice(tr, "DEV1", clock)
    job = svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101))
    assert job.status == OtaJobStatus.STREAMING
    assert dev.cmds[-1]["cmd"] == config.OTA_CMD_START
    assert dev.target_slot == "B"  # 非活跃分区
    assert len(dev.buf) == job.total_chunks

    dev.finish_download()
    dev.flash()  # active → 健康确认
    assert any(c["cmd"] == config.OTA_CMD_CONFIRM for c in dev.cmds)
    dev.report_result(config.OTA_RESULT_OK)
    assert svc.get_job("DEV1").status == OtaJobStatus.DONE

    v = svc.device_view("DEV1")
    assert v.active_slot == "B"
    assert v.current_version == 101


# ---- 2. 版本单调（R4）：提交后再次平级/降级被拒 --------------------
def test_version_monotonic_reject(key, tmp_path):
    tr, clock, svc = _make(key, tmp_path)
    dev = FakeDevice(tr, "DEV1", clock)
    svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101))
    dev.finish_download()
    dev.flash()
    dev.report_result(config.OTA_RESULT_OK)  # 提交，current=101

    with pytest.raises(VersionMonotonicError):
        svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101))  # 平级
    with pytest.raises(VersionMonotonicError):
        svc.submit_upgrade("DEV1", 50, package_blob=_blob(key, 50))   # 降级


# ---- 3. 断点续传：设备部分接收后补发缺失分片 -------------------
def test_resume(key, tmp_path):
    tr, clock, svc = _make(key, tmp_path)
    dev = FakeDevice(tr, "DEV1", clock)
    # 3 个分片（>CHUNK_SIZE）
    svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101, payload=b"X" * (1024 * 3)))
    before = len(tr.sent_log())
    dev.finish_download(last_seq=0)  # 声称仅收到第 0 片
    after = len(tr.sent_log())
    assert after > before  # 触发续传补发缺失分片
    data_count = sum(1 for e in tr.sent_log() if e[1].endswith("ota/data"))
    assert data_count >= 2  # 首轮 + 续传

    dev.finish_download()
    dev.flash()
    dev.report_result(config.OTA_RESULT_OK)
    assert svc.get_job("DEV1").status == OtaJobStatus.DONE


# ---- 4. 健康窗超时 → 自动回滚（R7）-----------------------------
def test_health_timeout_rollback(key, tmp_path):
    tr, clock, svc = _make(key, tmp_path)
    dev = FakeDevice(tr, "DEV1", clock)
    svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101))
    dev.finish_download()
    dev.flash(state=config.OTA_STATE_VERIFYING)  # 仅开窗，不确认
    assert svc.get_job("DEV1").status == OtaJobStatus.WAITING_HEALTH

    clock.t = 2000  # 超过 1000+300 窗
    rolled = svc.tick(2000)
    assert "DEV1" in rolled
    assert any(c["cmd"] == config.OTA_CMD_ROLLBACK for c in dev.cmds)
    assert svc.get_job("DEV1").status == OtaJobStatus.ROLLED_BACK

    dev.active = dev.committed = "A"
    dev.report_result(config.OTA_RESULT_ROLLBACK)
    v = svc.device_view("DEV1")
    assert v.active_slot == "A"
    assert v.ota_state == config.OTA_STATE_ROLLBACK


# ---- 5. 健康经遥测回报确认（R7 多路径）-------------------------
def test_health_via_telemetry(key, tmp_path):
    tr, clock, svc = _make(key, tmp_path)
    dev = FakeDevice(tr, "DEV1", clock)
    svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101))
    dev.finish_download()
    dev.flash(state=config.OTA_STATE_VERIFYING)  # 仅开窗，不确认
    assert svc.get_job("DEV1").status == OtaJobStatus.WAITING_HEALTH
    assert not any(c["cmd"] == config.OTA_CMD_CONFIRM for c in dev.cmds)

    tr.device_publish(
        build_topic("DEV1", config.TOPIC_TELEMETRY),
        json.dumps({"is_safe": True}).encode(),
    )
    assert any(c["cmd"] == config.OTA_CMD_CONFIRM for c in dev.cmds)
    dev.report_result(config.OTA_RESULT_OK)
    assert svc.get_job("DEV1").status == OtaJobStatus.DONE


# ---- 6. 异常隔离：非法载荷（含 dev_id）被忽略，不中断服务 -----
def test_malicious_progress_ignored(key, tmp_path):
    tr, clock, svc = _make(key, tmp_path)
    dev = FakeDevice(tr, "DEV1", clock)
    svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101))
    tr.device_publish(
        build_topic("DEV1", config.TOPIC_OTA_PROGRESS),
        json.dumps({"dev_id": "hack", "ota_state": "downloading"}).encode(),
    )
    # 单条非法消息被 schema 拒绝，服务继续运行
    assert svc.get_job("DEV1").status == OtaJobStatus.STREAMING
    # 正常流程仍可完成
    dev.finish_download()
    dev.flash()
    dev.report_result(config.OTA_RESULT_OK)
    assert svc.get_job("DEV1").status == OtaJobStatus.DONE


# ---- 7. 设备回报 fail：回退到上一稳定分区 ----------------------
def test_on_result_fail(key, tmp_path):
    tr, clock, svc = _make(key, tmp_path)
    dev = FakeDevice(tr, "DEV1", clock)
    svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101))
    dev.finish_download()
    dev.flash(state=config.OTA_STATE_VERIFYING)  # 仅开窗
    dev.report_result(config.OTA_RESULT_FAIL)
    job = svc.get_job("DEV1")
    assert job.status == OtaJobStatus.FAILED
    v = svc.device_view("DEV1")
    assert v.active_slot == "A"  # 回退到上一稳定
    assert v.ota_state == config.OTA_STATE_ROLLBACK


# ---- 8. 显式回滚（运维，中止在途升级）---------------------
def test_manual_rollback(key, tmp_path):
    tr, clock, svc = _make(key, tmp_path)
    dev = FakeDevice(tr, "DEV1", clock)
    svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101))
    dev.finish_download()
    dev.flash(state=config.OTA_STATE_VERIFYING)  # 在途，尚未提交
    assert svc.device_view("DEV1").active_slot == "A"  # 仍稳定于 A
    svc.request_rollback("DEV1")
    assert any(c["cmd"] == config.OTA_CMD_ROLLBACK for c in dev.cmds)
    assert svc.get_job("DEV1").status == OtaJobStatus.ROLLED_BACK
    assert svc.device_view("DEV1").active_slot == "A"  # 回退到上一稳定


# ---- 9. 遥测不健康（fault_level=4）→ 不确认 --------------
def test_health_telemetry_unhealthy_ignored(key, tmp_path):
    tr, clock, svc = _make(key, tmp_path)
    dev = FakeDevice(tr, "DEV1", clock)
    svc.submit_upgrade("DEV1", 101, package_blob=_blob(key, 101))
    dev.finish_download()
    dev.flash(state=config.OTA_STATE_VERIFYING)  # 开窗
    assert svc.get_job("DEV1").status == OtaJobStatus.WAITING_HEALTH
    tr.device_publish(
        build_topic("DEV1", config.TOPIC_TELEMETRY),
        json.dumps({"fault_level": 4}).encode(),  # 不健康
    )
    assert not any(c["cmd"] == config.OTA_CMD_CONFIRM for c in dev.cmds)
