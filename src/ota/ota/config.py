"""SSOT 派生的 OTA 常量（单一事实源，禁止在此之外另立常量）。

来源
----
- config/mqtt_topics.json  : 10 个 MQTT 主题
- docs/contract/adr-005-ota-ab.md : A/B 双分区物理地址 / FLAG / CHUNK / 健康窗 / EMQX
- docs/contract/adr-006-fault-tolerance.md : 传输专有字段不进统一字典

任何与契约冲突的改动须先过 tests/test_cross_module.py 门禁，并由主理人治理。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------------
# A/B 双分区（ADR-005）
# ---------------------------------------------------------------------------
FLASH_A_BASE = 0x08020000          # A 分区基址
FLASH_B_BASE = 0x08100000          # B 分区基址
PARTITION_CAPACITY = 0x0E0000      # 单分区容量上限 ~0.9MB
FLAG_SECTOR = 0x081E0000           # FLAG 扇区（位于 B 分区之后）
FLAG_PRIMARY_OFFSET = 0x000        # FLAG 主备份
FLAG_BACKUP_OFFSET = 0x200          # FLAG 备备份
FLAG_SECTOR_SIZE = 0x1000          # GD25Q127 扇区大小 4KB

CHUNK_SIZE = 1024                  # 分片大小（ADR-005）
HEALTH_WINDOW_S = 300              # 健康观测窗（秒，ADR-005）

EMQX_BROKER_URL = "mqtts://emqx.np-xltech.com:8883"
EMQX_HOST = "emqx.np-xltech.com"
EMQX_PORT = 8883
EMQX_TLS = True
EMQX_KEEPALIVE_S = 30

# ---------------------------------------------------------------------------
# 分区 / 槽位
# ---------------------------------------------------------------------------
SLOT_A = "A"
SLOT_B = "B"
SLOTS = (SLOT_A, SLOT_B)


def other_slot(slot: str) -> str:
    """返回对偶槽位（非活跃分区）。"""
    if slot == SLOT_A:
        return SLOT_B
    if slot == SLOT_B:
        return SLOT_A
    raise ValueError(f"非法槽位: {slot!r}")


def slot_base(slot: str) -> int:
    return FLASH_A_BASE if slot == SLOT_A else FLASH_B_BASE


# ---------------------------------------------------------------------------
# OTA 状态机取值（data_dictionary.json：ota_state / ota_result）
# ---------------------------------------------------------------------------
OTA_STATE_IDLE = "idle"
OTA_STATE_DOWNLOADING = "downloading"
OTA_STATE_FLASHING = "flashing"
OTA_STATE_VERIFYING = "verifying"
OTA_STATE_ACTIVE = "active"
OTA_STATE_ROLLBACK = "rollback"
OTA_STATES = {
    OTA_STATE_IDLE,
    OTA_STATE_DOWNLOADING,
    OTA_STATE_FLASHING,
    OTA_STATE_VERIFYING,
    OTA_STATE_ACTIVE,
    OTA_STATE_ROLLBACK,
}

OTA_RESULT_OK = "ok"
OTA_RESULT_FAIL = "fail"
OTA_RESULT_ROLLBACK = "rollback"
OTA_RESULTS = {OTA_RESULT_OK, OTA_RESULT_FAIL, OTA_RESULT_ROLLBACK}

# ---------------------------------------------------------------------------
# OTA 指令（ota/cmd 的 cmd 字段）—— 传输专有，不进 33 字段字典
# ---------------------------------------------------------------------------
OTA_CMD_START = "start"
OTA_CMD_PAUSE = "pause"
OTA_CMD_RESUME = "resume"
OTA_CMD_CONFIRM = "confirm"
OTA_CMD_ROLLBACK = "rollback"
OTA_CMDS = {OTA_CMD_START, OTA_CMD_PAUSE, OTA_CMD_RESUME, OTA_CMD_CONFIRM, OTA_CMD_ROLLBACK}

# ---------------------------------------------------------------------------
# 固件类型（framing header "type"）
# ---------------------------------------------------------------------------
FW_TYPE_FIRMWARE = 0x01
FW_TYPE_SMDL = 0x02
FW_TYPE_PARAMS = 0x03
FW_TYPES = {FW_TYPE_FIRMWARE, FW_TYPE_SMDL, FW_TYPE_PARAMS}

# ---------------------------------------------------------------------------
# 三级升级通道（对齐 mqtt_topics.json）
# ---------------------------------------------------------------------------
TOPIC_OTA_CMD = "ota/cmd"
TOPIC_OTA_DATA = "ota/data"
TOPIC_OTA_PROGRESS = "ota/progress"
TOPIC_OTA_RESULT = "ota/result"
TOPIC_PARAM_SET = "param/set"
TOPIC_TELEMETRY = "telemetry"
TOPIC_CONFIG_SMDL = "config/smdl"
TOPIC_INTERFERENCE_SYNC = "interference/sync"
TOPIC_AUDIT_LOG = "audit/log"
TOPIC_DIAG_LOG = "diag/log"

TOPIC_PATTERN = "rgv/{devId}/{topic}"

# 传输专有字段（ADR-006：仅作 MQTT 载荷内部字段或存 FLAG 扇区，不进 33 字段字典）
TRANSPORT_PRIVATE_FIELDS = {
    "seq", "crc", "signature", "pending", "health_deadline",
    "active_slot", "health_receipt", "chunk", "fw_type",
}
# 注：data_dictionary 中的 ota_active_slot 是上报字段（进字典）；
#     此处 FLAG 扇区内的 active_slot 是设备内部存储，不进字典，二者命名空间隔离。

MAGIC_PACKAGE = b"XLOT"      # 固件包魔数
MAGIC_FLAG = b"XLFG"          # FLAG 记录魔数


# ---------------------------------------------------------------------------
# 配置加载（从仓库 config/ 读取，保持与 SSOT 逐字一致）
# ---------------------------------------------------------------------------
def repo_root() -> Path:
    """定位仓库根（output/）。本文件位于 <root>/src/ota/ota/config.py。"""
    return Path(__file__).resolve().parents[3]


def load_topics_config() -> Dict[str, Any]:
    cfg_dir = Path(__file__).resolve().parents[3] / "config"
    if "XLPS2_CONFIG_DIR" in __import__("os").environ:
        cfg_dir = Path(__import__("os").environ["XLPS2_CONFIG_DIR"])
    with open(cfg_dir / "mqtt_topics.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_data_dictionary() -> Dict[str, Any]:
    cfg_dir = Path(__file__).resolve().parents[3] / "config"
    if "XLPS2_CONFIG_DIR" in __import__("os").environ:
        cfg_dir = Path(__import__("os").environ["XLPS2_CONFIG_DIR"])
    with open(cfg_dir / "data_dictionary.json", "r", encoding="utf-8") as f:
        return json.load(f)
