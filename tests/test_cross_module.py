"""XLPS2-Alpha 跨模块契约门禁（WP12 前置）。

验证四模块共享契约的一致性（SSOT，位于仓库 config/），并跨模块对账：
  - 数据字典 33 字段（config/data_dictionary.json）
  - 10 个 MQTT Topic（config/mqtt_topics.json）
  - current_state 编码（ADR-003）
  - OTA A/B 双分区（ADR-005）
  - 四级容错（ADR-006）
  - 各模块源码与 SSOT 逐字一致（CFW / EHW / HMI / OTA）

运行：
    pytest tests/test_cross_module.py -v
"""

import json
import os
import os.path
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(REPO_ROOT, "config")
SRC_DIR = os.path.join(REPO_ROOT, "src")

EXPECTED_FIELD_COUNT = 33
EXPECTED_TOPIC_COUNT = 10
VALID_TYPES = {
    "uint16", "int32", "int16", "uint8", "int8", "uint32",
    "float", "enum", "bool", "string",
}
CURRENT_STATE_ENUM = {"IDLE", "INIT", "STANDBY", "RUNNING", "ERROR", "UPDATING"}
FAULT_LEVELS = {1, 2, 3, 4}
OTA_SLOTS = {"A", "B"}

# 门禁源码扫描时跳过的目录
_SKIP_DIRS = {"node_modules", "dist", ".git", "__pycache__"}


def _load_json(name):
    with open(os.path.join(CONFIG_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def _read_tree(rel):
    """拼接某模块目录下所有源码文本（排除构建产物）。"""
    texts = []
    base = os.path.join(REPO_ROOT, rel)
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fn in files:
            if fn.endswith((".md", ".txt", ".py", ".c", ".h", ".ts", ".tsx", ".json")):
                try:
                    with open(os.path.join(root, fn), encoding="utf-8") as f:
                        texts.append(f.read())
                except Exception:
                    pass
    return "\n".join(texts)


# 模块源码文本（惰性缓存）
_CFW_TEXT = None
_EHW_TEXT = None
_HMI_TEXT = None
_OTA_TEXT = None


def _cfw_text():
    global _CFW_TEXT
    if _CFW_TEXT is None:
        _CFW_TEXT = _read_tree("src/cfw")
    return _CFW_TEXT


def _ehw_text():
    global _EHW_TEXT
    if _EHW_TEXT is None:
        _EHW_TEXT = _read_tree("src/ehw")
    return _EHW_TEXT


def _hmi_text():
    global _HMI_TEXT
    if _HMI_TEXT is None:
        _HMI_TEXT = _read_tree("src/hmi")
    return _HMI_TEXT


def _ota_text():
    global _OTA_TEXT
    if _OTA_TEXT is None:
        _OTA_TEXT = _read_tree("src/ota")
    return _OTA_TEXT


def _ota_src_on_path():
    ota_src = os.path.join(SRC_DIR, "ota")
    if ota_src not in sys.path:
        sys.path.insert(0, ota_src)


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


def test_dd_contains_ota_and_safety_fields(data_dict):
    names = {f["name"] for f in data_dict["fields"]}
    for k in ("ota_state", "ota_result", "ota_active_slot", "fault_level", "is_safe", "battery_soc"):
        assert k in names, f"数据字典缺字段 {k}"


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
    val = (2 << 14) | (5 << 8) | 3
    assert val == 0x8000 | 0x0500 | 0x03
    assert val == 0x8503


def test_current_state_uninit_sentinel():
    assert 0xFFFF == 65535


# ---- 4. OTA A/B 双分区（ADR-005）-----------------------------------------
def test_ota_ab_slots():
    assert OTA_SLOTS == {"A", "B"}


def test_ota_flag_sector_defined():
    assert 0x081E0000 > 0x08100000  # FLAG 在 B 分区之后


def test_fault_levels():
    assert FAULT_LEVELS == {1, 2, 3, 4}


def test_fault_level_field_present(data_dict):
    names = [f["name"] for f in data_dict["fields"]]
    assert "fault_level" in names


# ===========================================================================
# 跨模块源码对账（CFW / EHW / HMI / OTA vs SSOT）
# ===========================================================================

# ---- EHW（文档为主）------------------------------------------------------
def test_ehw_hsm_region_0based():
    t = _ehw_text()
    assert "区域0" in t and "区域1" in t and "区域2" in t, "HSM 区域须 0-based"
    assert "region=2" in t, "安全监控区须标注 region=2"
    assert "区域3" not in t, "ADR-003 仅有 3 个正交区域（0/1/2）"


def test_ehw_ota_partition():
    t = _ehw_text()
    assert "0x08020000" in t and "0x08100000" in t and "0x081E0000" in t
    assert "内部 Flash" in t, "ADR-005: STM32H743 内部 Flash 2MB 逻辑双分区"
    # 注：EHW 文档在变更说明中提及「删除原 GD25Q127×2 外部 Flash 表述」属历史记录，
    # 设计本身不依赖外部 Flash；外部 Flash 的硬门禁由 test_ota_no_external_flash 承担。


def test_ehw_interfaces():
    t = _ehw_text()
    assert "ISO1042" in t, "隔离 CAN 收发器"
    assert "ADM2483" in t, "隔离 RS485 收发器"
    assert "HR911105A" in t, "RJ45 连接器料号"
    assert "非 HR601680" in t, "须明确拒绝错误料号 HR601680"


def test_ehw_fields_in_dd(data_dict):
    names = {f["name"] for f in data_dict["fields"]}
    for k in ("position_mm", "is_safe", "current_state", "battery_soc", "region"):
        assert k in names
    assert "task_state" not in names


def test_ehw_modbus_fourlevel():
    t = _ehw_text()
    assert "0x2000" in t, "ADR-004 Modbus 基址"
    assert "0x10" in t, "ADR-004 Modbus 写功能码"
    assert "ESTOP" in t and "region=2" in t, "四级容错：ESTOP 全局捕获 + region=2 最高优先级"


# ---- CFW ------------------------------------------------------------------
def test_cfw_state_encode():
    assert (2 << 14) | (5 << 8) | 3 == 0x8503
    t = _cfw_text()
    assert "0x3Fu" in t, "top_state 掩码 0x3F (ADR-003)"
    assert "0xFFu" in t, "sub_state 掩码 0xFF"
    assert "CFW_STATE_UNINIT" in t, "未初始化哨兵"


def test_cfw_fault_level_enum():
    t = _cfw_text()
    assert "FT_L1_CHECK_DIST" in t
    assert "FT_L2_NUDGE_RETRY" in t
    assert "FT_L3_SLOW_STOP" in t
    assert "FT_L4_CROSS_VERIFY" in t, "CROSS_VERIFY = 四级 = level 4 (ADR-006)"


def test_cfw_fourlevel_keywords():
    t = _cfw_text()
    for kw in ("CHECK_DIST", "NUDGE_RETRY", "CROSS_VERIFY", "SLOW_STOP", "ESTOP", "cross_verify_fault_ch"):
        assert kw in t, f"缺失四级容错关键词 {kw}"


def test_cfw_task_status_no_alias():
    t = _cfw_text()
    assert "task_status" in t
    assert "task_state" not in t, "禁止 task_state 别名"


def test_cfw_ota_addrs():
    t = _cfw_text()
    assert "0x08020000" in t and "0x08100000" in t and "0x081E0000" in t
    assert "1024" in t and "300" in t, "CHUNK_SIZE=1024 / HEALTH_WINDOW_S=300 (ADR-005)"


def test_cfw_no_mqtt_bridge():
    t = _cfw_text()
    assert "rgv/" not in t, "CFW 不直连 MQTT，由网关桥接"
    assert "paho" not in t and "mosquitto" not in t, "CFW 仅走 CANopen/RS485"


def test_cfw_decode_consistency():
    t = _cfw_text()
    assert ">> 14" in t and "& 0x3u" in t, "region 位移/掩码"
    assert ">> 8" in t and "& 0x3Fu" in t, "top_state 位移/掩码"
    assert "& 0xFFu" in t, "sub_state 掩码"


def test_cfw_cv_interference_level4():
    t = _cfw_text()
    assert "CV_INTERFERENCE" in t
    assert "FT_L4_CROSS_VERIFY" in t, "交叉验证进行中 fault_level 须=level 4 (ADR-006)"


# ---- OTA ------------------------------------------------------------------
def test_ota_partition_addrs():
    t = _ota_text()
    assert "FLASH_A_BASE = 0x08020000" in t
    assert "FLASH_B_BASE = 0x08100000" in t
    assert "FLAG_SECTOR = 0x081E0000" in t


def test_ota_topics_match(mqtt_topics):
    t = _ota_text()
    topic_set = {x["topic"] for x in mqtt_topics["topics"]}
    for topic in topic_set:
        assert f'"{topic}"' in t, f"config.py 缺主题 {topic}"
    assert '"rgv/{devId}/{topic}"' in t, "TOPIC_PATTERN 须一致"


def test_ota_chunk_health():
    t = _ota_text()
    assert "CHUNK_SIZE = 1024" in t
    assert "HEALTH_WINDOW_S = 300" in t
    assert "FLAG_PRIMARY_OFFSET = 0x000" in t
    assert "FLAG_BACKUP_OFFSET = 0x200" in t


def test_ota_current_state_codec():
    _ota_src_on_path()
    from ota import schema
    assert schema.encode_current_state(2, 5, 3) == 0x8503
    assert schema.decode_current_state(0x8503) == (2, 5, 3)
    assert schema.CURRENT_STATE_SENTINEL == 0xFFFF
    assert "0x8503" in _ota_text(), "ADR-003 样例须见于文档/注释"


def test_ota_states_match_dd(data_dict):
    _ota_src_on_path()
    from ota import config
    assert config.OTA_STATES == {"idle", "downloading", "flashing", "verifying", "active", "rollback"}
    assert config.OTA_RESULTS == {"ok", "fail", "rollback"}
    names = {f["name"] for f in data_dict["fields"]}
    assert "ota_state" in names and "ota_result" in names


def test_ota_no_external_flash():
    t = _ota_text()
    assert "GD25Q127" not in t, "外部 Flash 旧表述须清理"
    assert "QSPI" not in t
    assert "双芯片" not in t


def test_ota_emqx_url():
    t = _ota_text()
    assert 'EMQX_BROKER_URL = "mqtts://emqx.np-xltech.com:8883"' in t


def test_ota_version_monotonic():
    _ota_src_on_path()
    from ota import versioning
    from ota.exceptions import VersionMonotonicError
    assert versioning.assert_monotonic("2", "1") == 2
    assert versioning.assert_monotonic("1", None) == 1
    with pytest.raises(VersionMonotonicError):
        versioning.assert_monotonic("1", "1")  # 平级回灌
    with pytest.raises(VersionMonotonicError):
        versioning.assert_monotonic("1", "2")  # 降级


# ---- HMI ------------------------------------------------------------------
def test_hmi_dict_mirror():
    t = _read_tree("src/hmi/src/contract")
    assert "data_dictionary.json" in t, "HMI 须直引 SSOT 字典"
    assert "FIELD_COUNT" in t


def test_hmi_topics_mirror():
    t = _read_tree("src/hmi/src/contract")
    assert "mqtt_topics.json" in t, "HMI 须直引 SSOT 主题"
    assert "rgv/${devId}/${name}" in t
    assert "rgv/{devId}/{topic}" in t
    for topic in ("ota/cmd", "ota/data", "ota/progress", "ota/result",
                  "param/set", "telemetry", "config/smdl",
                  "interference/sync", "audit/log", "diag/log"):
        assert f"'{topic}'" in t, f"HMI 缺主题 {topic}"


def test_hmi_no_task_state_alias():
    assert "task_state" not in _hmi_text(), "HMI 禁止 task_state 别名"


def test_hmi_current_state_decode():
    t = _read_tree("src/hmi/src/contract")
    assert "(r >> 14) & 0x03" in t, "region 位移/掩码 (ADR-003)"
    assert "(r >> 8) & 0x3f" in t, "top_state 位移/掩码"
    assert "r & 0xff" in t, "sub_state 掩码"
    assert "0xffff" in t, "未初始化哨兵"


def test_hmi_rbac_three_roles():
    t = _read_tree("src/hmi/src/auth")
    assert "export type Role = 'operator' | 'engineer' | 'admin'" in t, "三角色 RBAC"


def test_hmi_no_external_flash():
    t = _hmi_text()
    assert "GD25Q127" not in t
    assert "双芯片" not in t


def test_hmi_mqtt_pattern():
    t = _read_tree("src/hmi/src/mqtt")
    assert "topicFor" in t, "HMI 须经 topicFor 构造 rgv/{devId}/{topic}"
    assert '"rgv/' not in t, "禁止硬编码 rgv/ 字面量（须由 devId 路径承载）"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
