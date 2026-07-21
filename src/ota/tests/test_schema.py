"""载荷校验与传输专有字段隔离（ADR-006 / R15 异常隔离）。"""
import json

import pytest

from ota import config
from ota.exceptions import SchemaError
from ota.schema import (
    assert_transport_isolation,
    validate_ota_cmd,
    validate_ota_data,
    validate_ota_progress,
    validate_ota_result,
)


def test_validate_ota_cmd_ok():
    validate_ota_cmd({"cmd": "start", "target_version": "101", "slot": "B"})


@pytest.mark.parametrize(
    "payload",
    [
        {"cmd": "bogus", "target_version": "101", "slot": "B"},
        {"cmd": "start", "target_version": "abc", "slot": "B"},
        {"cmd": "start", "target_version": "101", "slot": "X"},
        {"cmd": "start", "target_version": "101"},  # 缺 slot
        {"cmd": "start", "slot": "B"},                    # 缺 version
    ],
)
def test_validate_ota_cmd_rejects(payload):
    with pytest.raises(SchemaError):
        validate_ota_cmd(payload)


def test_validate_ota_data_ok():
    obj = {"total": 3, "ftype": 1, "version": "101",
           "chunks": [{"seq": 0, "crc": 1, "chunk": "AAAA"}]}
    validate_ota_data(obj)


def test_validate_ota_data_rejects():
    with pytest.raises(SchemaError):
        validate_ota_data({"total": 3})  # 缺字段
    with pytest.raises(SchemaError):
        validate_ota_data({"total": 3, "ftype": 1, "version": "1", "chunks": "x"})  # chunks 非数组


def test_validate_ota_progress_ok_and_resume():
    validate_ota_progress({
        "ota_state": "downloading", "ota_active_slot": "B",
        "ota_progress_pct": 50, "ota_target_version": "101",
        "last_seq": 2,  # 续传控制：允许的内部传输字段
    })


def test_validate_ota_progress_rejects_illegal_field():
    with pytest.raises(SchemaError):
        validate_ota_progress({"ota_state": "downloading", "foo": 1})


def test_validate_ota_progress_rejects_dev_id():
    with pytest.raises(SchemaError):
        validate_ota_progress({"ota_state": "downloading", "dev_id": "x"})


def test_validate_ota_progress_rejects_bad_state():
    with pytest.raises(SchemaError):
        validate_ota_progress({"ota_state": "bogus"})


def test_validate_ota_progress_rejects_bad_pct():
    with pytest.raises(SchemaError):
        validate_ota_progress({"ota_progress_pct": 150})


def test_validate_ota_result_ok():
    for r in ("ok", "fail", "rollback"):
        validate_ota_result({"ota_result": r})


def test_validate_ota_result_rejects():
    with pytest.raises(SchemaError):
        validate_ota_result({"ota_result": "maybe"})
    with pytest.raises(SchemaError):
        validate_ota_result({"dev_id": "x", "ota_result": "ok"})


def test_transport_fields_not_in_dictionary():
    """SSOT 一致性：33 字段字典不得含传输专有字段（ADR-006）。"""
    dd = config.load_data_dictionary()
    names = {f["name"] for f in dd["fields"]}
    assert len(names) == 33
    leaked = config.TRANSPORT_PRIVATE_FIELDS & names
    assert leaked == set(), f"传输专有字段泄漏进字典: {leaked}"
    # 显式自检接口
    assert_transport_isolation(names)
