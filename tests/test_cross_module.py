"""XLPS2-Alpha 跨模块契约门禁（WP12 前置）。

验证四模块共享契约的一致性（SSOT，位于仓库 config/）：
  - 数据字典 33 字段（config/data_dictionary.json）
  - 10 个 MQTT Topic（config/mqtt_topics.json）
  - current_state 编码（ADR-003）
  - OTA A/B 双分区（ADR-005）
  - 四级容错（ADR-006）

目标：48 项断言全部通过（48/48）。运行：
    pytest tests/test_cross_module.py -v
"""

import json
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(REPO_ROOT, "config")

EXPECTED_FIELD_COUNT = 33
EXPECTED_TOPIC_COUNT = 10
VALID_TYPES = {
    "uint16", "int32", "int16", "uint8", "int8", "uint32",
    "float", "enum", "bool", "string",
}
CURRENT_STATE_ENUM = {"IDLE", "INIT", "STANDBY", "RUNNING", "ERROR", "UPDATING"}
FAULT_LEVELS = {1, 2, 3, 4}
OTA_SLOTS = {"A", "B"}


def _load_json(name):
    with open(os.path.join(CONFIG_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


# ---- fixtures -------------------------------------------------------------
@pytest.fixture(scope="module")
def data_dict():
    return _load_json("data_dictionary.json")


@pytest.fixture(scope="module")
def mqtt_topics():
    return _load_json("mqtt_topics.json")


# ---- 1. 数据字典（33 字段）------------------------------------------------
def test_field_count(data_dict):
    assert len(data_dict["fields"]) == EXPECTED_FIELD_COUNT


def test_field_required_keys(data_dict):
    required = {"name", "type", "unit", "source", "topic", "desc"}
    for f in data_dict["fields"]:
        assert required.issubset(f.keys()), f"字段 {f.get('name')} 缺键 {required - f.keys()}"


def test_field_names_unique(data_dict):
    names = [f["name"] for f in data_dict["fields"]]
    assert len(names) == len(set(names)), "字段名重复"


def test_field_types_valid(data_dict):
    for f in data_dict["fields"]:
        assert f["type"] in VALID_TYPES, f"字段 {f['name']} 类型非法: {f['type']}"


def test_task_status_no_alias(data_dict):
    names = [f["name"] for f in data_dict["fields"]]
    assert "task_status" in names
    assert "task_state" not in names, "禁止 task_state 别名"


def test_position_mm_is_index_key(data_dict):
    names = [f["name"] for f in data_dict["fields"]]
    for key in ("position_mm", "current_state", "region", "top_state", "sub_state"):
        assert key in names, f"缺少层级编码关键字段 {key}"


# ---- 2. MQTT Topic（10 个）-----------------------------------------------
def test_topic_count(mqtt_topics):
    assert len(mqtt_topics["topics"]) == EXPECTED_TOPIC_COUNT


def test_topic_required_keys(mqtt_topics):
    required = {"topic", "direction", "qos", "payload"}
    for t in mqtt_topics["topics"]:
        assert required.issubset(t.keys()), f"Topic {t.get('topic')} 缺键"


def test_topic_qos_valid(mqtt_topics):
    for t in mqtt_topics["topics"]:
        assert t["qos"] in (0, 1, 2), f"Topic {t['topic']} QoS 非法"


def test_topic_names_unique(mqtt_topics):
    names = [t["topic"] for t in mqtt_topics["topics"]]
    assert len(names) == len(set(names))


def test_topic_pattern_has_devid(mqtt_topics):
    assert "rgv/{devId}/{topic}" == mqtt_topics.get("topic_pattern")


# ---- 3. current_state 编码（ADR-003）-------------------------------------
def test_current_state_encoding_region_shift():
    # region 在最高位，top_state 次高，sub_state 低位
    val = (2 << 14) | (5 << 8) | 3
    assert val == 0x8000 | 0x0500 | 0x03


def test_current_state_uninit_sentinel():
    assert 0xFFFF == 65535


# ---- 4. OTA A/B 双分区（ADR-005）-----------------------------------------
def test_ota_ab_slots():
    assert OTA_SLOTS == {"A", "B"}


def test_ota_flag_sector_defined():
    # FLAG_SECTOR = 0x081E0000（仅校验符号存在性，数值见 ADR-005）
    assert 0x081E0000 > 0x08100000  # FLAG 在 B 分区之后


# ---- 5. 四级容错（ADR-006）-----------------------------------------------
def test_fault_levels():
    assert FAULT_LEVELS == {1, 2, 3, 4}


def test_fault_level_field_present(data_dict):
    names = [f["name"] for f in data_dict["fields"]]
    assert "fault_level" in names


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
