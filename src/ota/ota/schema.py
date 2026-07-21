"""OTA 载荷校验（不可绕过；传输专有字段不污染 33 字段字典，ADR-006）。

设计
----
- 33 字段统一字典是跨模块 SSOT；OTA 上报字段（ota_state / ota_progress_pct /
  ota_active_slot / ota_target_version / ota_result）必须严格落在字典内。
- 传输专有字段（seq / crc / signature / pending / health_deadline / 健康回执 /
  last_seq 续传控制）**可**作为 MQTT 载荷内部字段存在（ADR-006 明确允许），
  但**绝不**进入 33 字段字典，且须经白名单校验，杜绝任意字段注入。
- devId 由 Topic 路径承载，**禁止**出现在 payload（治理 / ADR-002）。

所有 OTA 入口处理前必须过对应 validate_*，否则抛 ``SchemaError``。
"""
from __future__ import annotations

from typing import Any, Dict

from . import config
from .exceptions import SchemaError

# 字典内 OTA 上报字段（data_dictionary.json，topic=ota/progress | ota/result）
_PROGRESS_DICT_FIELDS = {
    "ota_state", "ota_progress_pct", "ota_active_slot", "ota_target_version",
}
_RESULT_DICT_FIELDS = {"ota_result"}

# 传输专有「控制」字段白名单（MQTT 载荷内部字段，不进字典，ADR-006）
_PROGRESS_TRANSPORT_FIELDS = {"last_seq"}   # 续传控制：设备已连续收到的最高 seq
_CMD_TRANSPORT_FIELDS = {"cmd", "target_version", "slot", "pending"}
_DATA_TRANSPORT_FIELDS = {"total", "ftype", "version", "chunks"}

_DEV_ID_KEYS = {"dev_id", "device_id", "devId", "deviceId"}


def _reject_dev_id(payload: Dict[str, Any]) -> None:
    for k in payload:
        if k in _DEV_ID_KEYS:
            raise SchemaError(f"devId 禁止进入 payload（须由 Topic 路径承载）: 字段 {k!r}")


def _assert_dict_fields(name: str, payload: Dict[str, Any], allowed: set, transport: set) -> None:
    for k in payload:
        if k in allowed:
            continue
        if k in transport:
            # 传输专有字段：仅允许白名单内的值，且不进入字典
            continue
        raise SchemaError(f"{name} 含非法字段 {k!r}（须为字典字段 {allowed} 或传输白名单 {transport}）")


def validate_ota_cmd(payload: Dict[str, Any]) -> None:
    """校验 ota/cmd（cloud→device 指令信封）。"""
    if not isinstance(payload, dict):
        raise SchemaError("ota/cmd payload 须为对象")
    _reject_dev_id(payload)
    cmd = payload.get("cmd")
    if cmd not in config.OTA_CMDS:
        raise SchemaError(f"ota/cmd.cmd 非法: {cmd!r}")
    if cmd == config.OTA_CMD_START:
        tv = payload.get("target_version")
        slot = payload.get("slot")
        if tv is None or not str(tv).isdigit():
            raise SchemaError(f"start 须带十进制整数字符串 target_version，收到 {tv!r}")
        if slot not in config.SLOTS:
            raise SchemaError(f"start.slot 须为 A/B，收到 {slot!r}")
    # 其余键必须是传输白名单
    _assert_dict_fields("ota/cmd", payload, set(), _CMD_TRANSPORT_FIELDS)


def validate_ota_data(payload: Dict[str, Any]) -> None:
    """校验 ota/data（分片信封：total / ftype / version / chunks[seq,crc,chunk]）。"""
    if not isinstance(payload, dict):
        raise SchemaError("ota/data payload 须为对象")
    _reject_dev_id(payload)
    for req in ("total", "ftype", "version", "chunks"):
        if req not in payload:
            raise SchemaError(f"ota/data 缺字段 {req!r}")
    if not isinstance(payload["chunks"], list):
        raise SchemaError("ota/data.chunks 须为数组")
    for c in payload["chunks"]:
        for req in ("seq", "crc", "chunk"):
            if req not in c:
                raise SchemaError(f"ota/data chunk 缺字段 {req!r}")
    _assert_dict_fields("ota/data", payload, set(), _DATA_TRANSPORT_FIELDS)


def validate_ota_progress(payload: Dict[str, Any]) -> None:
    """校验 ota/progress（字典字段 + 允许续传控制 last_seq）。"""
    if not isinstance(payload, dict):
        raise SchemaError("ota/progress payload 须为对象")
    _reject_dev_id(payload)
    if "ota_state" in payload and payload["ota_state"] not in config.OTA_STATES:
        raise SchemaError(f"ota_state 非法: {payload['ota_state']!r}")
    if "ota_active_slot" in payload and payload["ota_active_slot"] not in config.SLOTS:
        raise SchemaError(f"ota_active_slot 非法: {payload['ota_active_slot']!r}")
    if "ota_progress_pct" in payload:
        pct = payload["ota_progress_pct"]
        if not isinstance(pct, int) or not (0 <= pct <= 100):
            raise SchemaError(f"ota_progress_pct 须 0-100，收到 {pct!r}")
    if "ota_target_version" in payload and not str(payload["ota_target_version"]).isdigit():
        raise SchemaError("ota_target_version 须为十进制整数字符串")
    if "last_seq" in payload and (not isinstance(payload["last_seq"], int) or payload["last_seq"] < 0):
        raise SchemaError("last_seq 须为非负整数（续传控制）")
    _assert_dict_fields("ota/progress", payload, _PROGRESS_DICT_FIELDS, _PROGRESS_TRANSPORT_FIELDS)


def validate_ota_result(payload: Dict[str, Any]) -> None:
    """校验 ota/result（ota_result ∈ {ok,fail,rollback}）。"""
    if not isinstance(payload, dict):
        raise SchemaError("ota/result payload 须为对象")
    _reject_dev_id(payload)
    res = payload.get("ota_result")
    if res not in config.OTA_RESULTS:
        raise SchemaError(f"ota_result 非法: {res!r}")
    _assert_dict_fields("ota/result", payload, _RESULT_DICT_FIELDS, set())


def assert_transport_isolation(dictionary_fields: set) -> None:
    """SSOT 一致性自检：传输专有字段不得出现在 33 字段字典里。"""
    leaked = config.TRANSPORT_PRIVATE_FIELDS & dictionary_fields
    if leaked:
        raise SchemaError(f"传输专有字段泄漏进数据字典: {leaked}")


# ---------------------------------------------------------------------------
# ADR-003 current_state 层级编码（与 HMI contract/types.ts 逐字节一致）
# ---------------------------------------------------------------------------
# current_state 为 16 位 uint16，三段不重叠：
#   sub_state  = bits 0–7  （8 位，掩码 0x00FF）
#   top_state  = bits 8–13 （6 位，掩码 0x3F）
#   region     = bits 14–15（2 位，掩码 0x03）
# 编码公式：(region<<14) | (top_state<<8) | sub_state
# 哨兵：0xFFFF = 未初始化。
# 跨模块门禁样例：(2<<14)|(5<<8)|3 == 0x8503。
CURRENT_STATE_SENTINEL = 0xFFFF
_REGION_MASK = 0x03
_TOP_STATE_MASK = 0x3F
_SUB_STATE_MASK = 0x00FF


def encode_current_state(region: int, top_state: int, sub_state: int) -> int:
    """按 ADR-003 编码 ``(region<<14)|(top_state<<8)|sub_state``。"""
    if not isinstance(region, int) or not (0 <= region <= _REGION_MASK):
        raise SchemaError(f"region 须 0..{_REGION_MASK}，收到 {region!r}")
    if not isinstance(top_state, int) or not (0 <= top_state <= _TOP_STATE_MASK):
        raise SchemaError(f"top_state 须 0..{_TOP_STATE_MASK}，收到 {top_state!r}")
    if not isinstance(sub_state, int) or not (0 <= sub_state <= _SUB_STATE_MASK):
        raise SchemaError(f"sub_state 须 0..{_SUB_STATE_MASK}，收到 {sub_state!r}")
    return (
        (region & _REGION_MASK) << 14
        | (top_state & _TOP_STATE_MASK) << 8
        | (sub_state & _SUB_STATE_MASK)
    )


def decode_current_state(value: int) -> "tuple[int, int, int]":
    """按 ADR-003 解码为 (region, top_state, sub_state)。

    0xFFFF 哨兵表示未初始化，解码无意义，抛 ``SchemaError``。
    """
    if not isinstance(value, int) or value < 0 or value > 0xFFFF:
        raise SchemaError(f"current_state 须为 0..0xFFFF 的 uint16，收到 {value!r}")
    if value == CURRENT_STATE_SENTINEL:
        raise SchemaError("current_state=0xFFFF 表示未初始化，不可解码")
    region = (value >> 14) & _REGION_MASK
    top_state = (value >> 8) & _TOP_STATE_MASK
    sub_state = value & _SUB_STATE_MASK
    return region, top_state, sub_state
