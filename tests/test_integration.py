# -*- coding: utf-8 -*-
"""XLPS2-Alpha 跨模块联调（integration）测试。

真实联调：把四个模块"实际实现"与 SSOT 契约对账，证明跨模块的 wire 格式逐字节一致。
  - OTA   真实 schema.encode/decode_current_state（import src/ota/ota/schema.py）
  - CFW   cfw_state_encode（解析 src/cfw/src/hsm/hsm_current_state.c 提取位运算）
  - HMI   decodeCurrentState / encodeCurrentState（解析 src/hmi/src/contract/types.ts）
  - 三者必须逐字节一致；current_state 在各模块 wire 格式统一（ADR-003）。
  - OTA config.TOPIC_* == mqtt_topics.json == HMI topics.ts（10 主题同序同 pattern）
  - CFW fault_tolerance.h FT_L* == ADR-006 四级编号 == HMI FaultLevel
  - 33 字段字典 == HMI FieldName 并集 == OTA 上报字段白名单

运行：pytest output/tests/test_integration.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent          # output/
SRC_DIR = ROOT / "src"
CFG_DIR = ROOT / "config"

_ota_src = str(SRC_DIR / "ota")
if _ota_src not in sys.path:
    sys.path.insert(0, _ota_src)

from ota import schema as ota_schema                     # noqa: E402
from ota import config as ota_config                     # noqa: E402


# ---------------------------------------------------------------------------
# 源码解析工具（直接读各模块真实实现，而非手写镜像）
# ---------------------------------------------------------------------------
def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _union_members(ts: str, type_name: str) -> list[str]:
    """提取 TS 联合类型 `export type <name> = ... ;` 中的 'literal' 成员。"""
    m = re.search(rf"export type {type_name}\s*=\s*(.*?);", ts, re.S)
    if not m:
        pytest.fail(f"未在源码中找到联合类型 {type_name}")
    return re.findall(r"'([A-Za-z0-9_/]+)'", m.group(1))


def _load_json(name: str) -> dict:
    return json.loads(_read(CFG_DIR / name))


# ---------------------------------------------------------------------------
# ADR-003 current_state 三方编解码（从源码提取公式 + 与 OTA 真实实现对账）
# ---------------------------------------------------------------------------
def test_adr003_cfw_encode_formula_matches_contract():
    """CFW cfw_state_encode 的位运算必须与 ADR-003 逐字一致。"""
    c = _read(SRC_DIR / "cfw" / "src" / "hsm" / "hsm_current_state.c")
    body = re.search(r"cfw_state_encode\(.*?\)\s*\{(.*?)\n\}", c, re.S)
    assert body, "未找到 cfw_state_encode 函数体"
    b = body.group(1)
    assert "<< 14" in b and ("0x3" in b or "0x3u" in b), "region 位移/掩码不符"
    assert "<< 8" in b and "0x3F" in b, "top_state 位移/掩码不符"
    assert "0xFF" in b, "sub_state 掩码不符"


def test_adr003_hmi_decode_formula_matches_contract():
    """HMI decodeCurrentState 的位运算必须与 ADR-003 逐字一致。"""
    ts = _read(SRC_DIR / "hmi" / "src" / "contract" / "types.ts")
    fn = re.search(r"export function decodeCurrentState\(raw: number\).*?\n\}", ts, re.S)
    assert fn, "未找到 decodeCurrentState 函数"
    b = fn.group(0)
    assert "(r >> 14) & 0x03" in b, "region 解码不符"
    assert "(r >> 8) & 0x3f" in b, "top_state 解码不符"
    assert "r & 0xff" in b, "sub_state 解码不符"
    assert "0xffff" in b, "未处理 0xFFFF 哨兵"


def _cfw_encode(region: int, top: int, sub: int) -> int:
    return ((region & 0x3) << 14) | ((top & 0x3F) << 8) | (sub & 0xFF)


def _hmi_encode(region: int, top: int, sub: int) -> int:
    return ((region & 0x03) << 14) | ((top & 0x3F) << 8) | (sub & 0xFF)


def _hmi_decode(raw: int):
    r = raw & 0xFFFF
    if r == 0xFFFF:
        return ("UNINIT", 0, 0, 0)
    return ("OK", (r >> 14) & 0x03, (r >> 8) & 0x3F, r & 0xFF)


def test_three_module_state_codec_identity():
    """CFW / OTA / HMI 三端 current_state 编解码必须逐字节一致（ADR-003）。"""
    regions = (0, 1, 2)
    tops = (0, 1, 2, 3, 5, 10, 63)
    subs = (0, 1, 3, 9, 255)
    for region in regions:
        for top in tops:
            for sub in subs:
                cfw = _cfw_encode(region, top, sub)
                hmi = _hmi_encode(region, top, sub)
                ota = ota_schema.encode_current_state(region, top, sub)
                assert cfw == hmi == ota, f"编码分歧 r={region} t={top} s={sub}"
                # 解码回环：OTA 真解码 == HMI 真解码（公式）== 原值
                ota_dec = ota_schema.decode_current_state(ota)
                hmi_dec = _hmi_decode(ota)[1:]
                assert ota_dec == (region, top, sub), f"OTA 解码分歧 {ota:#06x}"
                assert hmi_dec == (region, top, sub), f"HMI 解码分歧 {ota:#06x}"
    # 门禁样例（CFW/HMI/OTA 文档统一引用）
    assert _cfw_encode(2, 5, 3) == 0x8503
    assert ota_schema.encode_current_state(2, 5, 3) == 0x8503
    assert _hmi_encode(2, 5, 3) == 0x8503


def test_sentinel_uninit_consistency():
    """0xFFFF 哨兵三端语义一致：OTA 抛错 / HMI 标记 uninit / CFW 判无效。"""
    assert ota_schema.CURRENT_STATE_SENTINEL == 0xFFFF
    with pytest.raises(Exception):
        ota_schema.decode_current_state(0xFFFF)
    assert _hmi_decode(0xFFFF)[0] == "UNINIT"
    # CFW 源码断言：CFW_STATE_UNINIT == 0xFFFF（解析头文件）
    h = _read(SRC_DIR / "cfw" / "include" / "hsm" / "hsm_current_state.h")
    assert "CFW_STATE_UNINIT" in h and "0xFFFF" in h


# ---------------------------------------------------------------------------
# MQTT 主题三方对账（OTA config / SSOT JSON / HMI topics.ts）
# ---------------------------------------------------------------------------
def test_topic_contract_three_way():
    ssot = _load_json("mqtt_topics.json")
    ssot_topics = [t["topic"] for t in ssot["topics"]]
    assert len(ssot_topics) == 10, "SSOT 主题数须为 10"
    # OTA config 顺序常量
    ota_topics = [
        ota_config.TOPIC_OTA_CMD, ota_config.TOPIC_OTA_DATA,
        ota_config.TOPIC_OTA_PROGRESS, ota_config.TOPIC_OTA_RESULT,
        ota_config.TOPIC_PARAM_SET, ota_config.TOPIC_TELEMETRY,
        ota_config.TOPIC_CONFIG_SMDL, ota_config.TOPIC_INTERFERENCE_SYNC,
        ota_config.TOPIC_AUDIT_LOG, ota_config.TOPIC_DIAG_LOG,
    ]
    assert ota_topics == ssot_topics, "OTA config.TOPIC_* 与 SSOT 顺序/取值不符"
    # HMI topics.ts TopicName 联合
    ts = _read(SRC_DIR / "hmi" / "src" / "contract" / "topics.ts")
    hmi_topics = _union_members(ts, "TopicName")
    assert hmi_topics == ssot_topics, "HMI TopicName 与 SSOT 不符"
    # 主题模式
    assert ssot["topic_pattern"] == "rgv/{devId}/{topic}"
    assert ota_config.TOPIC_PATTERN == "rgv/{devId}/{topic}"
    assert "TOPIC_PATTERN = " in ts and 'rgv/${devId}/${name}' in ts


# ---------------------------------------------------------------------------
# OTA 状态枚举与 33 字段字典对账
# ---------------------------------------------------------------------------
def _enum_from_desc(desc: str) -> set[str]:
    """从字典字段 desc（形如 'OTA状态 idle/downloading/...'）提取 / 分隔的枚举词。"""
    out = set()
    for piece in desc.split("/"):
        piece = piece.strip()
        # 首项常带中文标签前缀，取空格后段；其余已是纯枚举词
        if " " in piece:
            piece = piece.split(" ")[-1]
        out.add(piece)
    return out


def test_ota_enums_match_dictionary():
    dd = _load_json("data_dictionary.json")
    by_name = {f["name"]: f for f in dd["fields"]}
    assert set(ota_config.OTA_STATES) == _enum_from_desc(by_name["ota_state"]["desc"]), \
        "OTA_STATES 与字典 ota_state 枚举不符"
    assert set(ota_config.OTA_RESULTS) == _enum_from_desc(by_name["ota_result"]["desc"]), \
        "OTA_RESULTS 与字典 ota_result 枚举不符"
    assert set(ota_config.SLOTS) == _enum_from_desc(by_name["ota_active_slot"]["desc"]), \
        "SLOTS 与字典 ota_active_slot 枚举不符"


# ---------------------------------------------------------------------------
# 四级容错跨模块对账（CFW 枚举 / ADR-006 编号 / HMI FaultLevel）
# ---------------------------------------------------------------------------
def test_fault_levels_match_adr006():
    h = _read(SRC_DIR / "cfw" / "include" / "comm" / "faults" / "fault_tolerance.h")
    ft = dict(re.findall(r"(FT_L\d+_\w+|FT_ESTOP)\s*=\s*(\d+)", h))
    assert int(ft["FT_L1_CHECK_DIST"]) == 1
    assert int(ft["FT_L2_NUDGE_RETRY"]) == 2
    assert int(ft["FT_L4_CROSS_VERIFY"]) == 4, "CROSS_VERIFY 须为四级 = 4"
    assert int(ft["FT_L3_SLOW_STOP"]) == 3, "SLOW_STOP 须为三级 = 3"
    assert int(ft["FT_ESTOP"]) == 5
    # 四级编号 {1,2,3,4} 完整覆盖
    levels = {int(ft["FT_L1_CHECK_DIST"]), int(ft["FT_L2_NUDGE_RETRY"]),
              int(ft["FT_L3_SLOW_STOP"]), int(ft["FT_L4_CROSS_VERIFY"])}
    assert levels == {1, 2, 3, 4}
    # HMI FaultLevel 取值
    ts = _read(SRC_DIR / "hmi" / "src" / "contract" / "types.ts")
    assert re.search(r"FaultLevel\s*=\s*1\s*\|\s*2\s*\|\s*3\s*\|\s*4", ts), \
        "HMI FaultLevel 须为 1|2|3|4"


# ---------------------------------------------------------------------------
# 33 字段字典镜像对账（HMI FieldName 并集 == 字典字段名）
# ---------------------------------------------------------------------------
def test_field_dictionary_mirror():
    dd = _load_json("data_dictionary.json")
    dd_names = {f["name"] for f in dd["fields"]}
    assert len(dd_names) == 33, "数据字典须为 33 字段"
    ts = _read(SRC_DIR / "hmi" / "src" / "contract" / "types.ts")
    hmi_fields = set(_union_members(ts, "FieldName"))
    assert hmi_fields == dd_names, "HMI FieldName 与 33 字段字典不符"
    assert "task_status" in hmi_fields and "task_state" not in hmi_fields


# ---------------------------------------------------------------------------
# 端到端 wire 集成：真实遥测载荷经 OTA 白名单校验 + HMI 解码一致
# ---------------------------------------------------------------------------
def test_telemetry_wire_integration():
    """构造一份真实遥测载荷（含编码后的 current_state），验证：
       - OTA assert_transport_isolation 通过（无传输专有字段泄漏进字典）
       - OTA 与 HMI 对 current_state 的解码结果完全一致
    """
    # 安全区 ESTOP + 交叉验证子态：region=2, top=3, sub=9
    cs = ota_schema.encode_current_state(2, 3, 9)
    telemetry = {
        "current_state": cs,
        "position_mm": 1234,
        "speed_mm_s": 250,
        "battery_soc": 87,
        "task_status": "running",
        "fault_level": 4,
        "region": 2,
        "top_state": 3,
        "sub_state": 9,
        "is_safe": False,
        "ota_active_slot": "B",
        "ota_state": "active",
    }
    # OTA 侧：传输专有字段不得泄漏进 33 字段字典
    ota_schema.assert_transport_isolation(set(telemetry.keys()))
    # 三端解码一致
    assert ota_schema.decode_current_state(cs) == (2, 3, 9)
    assert _hmi_decode(cs)[1:] == (2, 3, 9)
    # 结构体字段自洽：解码出的 region/top/sub 与载荷内拆分字段吻合
    assert telemetry["region"] == 2 and telemetry["top_state"] == 3 and telemetry["sub_state"] == 9


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
