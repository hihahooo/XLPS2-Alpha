"""MQTT 主题构造 / 解析 / 内存传输路由测试。"""
import json

import pytest

from ota.mqtt_adapter import InMemoryTransport, _topic_match
from ota.topics import build_topic, parse_topic


def test_topic_roundtrip():
    t = build_topic("DEV9", "ota/cmd")
    assert t == "rgv/DEV9/ota/cmd"
    dev, rel = parse_topic(t)
    assert dev == "DEV9" and rel == "ota/cmd"


def test_devid_must_not_contain_slash():
    with pytest.raises(ValueError):
        build_topic("DEV/9", "ota/cmd")  # devId 须由路径承载


def test_parse_invalid():
    with pytest.raises(ValueError):
        parse_topic("ota/cmd")          # 缺 rgv/ 前缀
    with pytest.raises(ValueError):
        parse_topic("rgv//ota/cmd")     # 空 devId


def test_all_topic_relpaths():
    from ota.topics import all_topic_relpaths, config_load_topic_count

    assert config_load_topic_count() == 10
    rels = all_topic_relpaths()
    assert len(rels) == 10
    assert "ota/cmd" in rels and "telemetry" in rels


def test_parse_topic_branches():
    from ota.topics import parse_topic

    with pytest.raises(ValueError):
        parse_topic("rgv")            # 段数不足
    with pytest.raises(ValueError):
        parse_topic("x/y/z")          # 非 rgv 前缀


def test_is_ota_topic():
    from ota.topics import is_ota_topic

    assert is_ota_topic("rgv/DEV/ota/cmd") is True
    assert is_ota_topic("rgv/DEV/ota/data") is True
    assert is_ota_topic("rgv/DEV/telemetry") is False


def test_ota_topics():
    from ota.topics import ota_topics

    t = ota_topics("DEV7")
    assert t["cmd"].endswith("ota/cmd")
    assert t["data"].endswith("ota/data")
    assert t["progress"].endswith("ota/progress")
    assert t["result"].endswith("ota/result")


def test_topic_match():
    assert _topic_match("rgv/+/ota/progress", "rgv/DEV1/ota/progress")
    assert not _topic_match("rgv/DEV1/ota/progress", "rgv/DEV2/ota/progress")
    assert _topic_match("rgv/+/+/#", "rgv/DEV1/ota/progress")
    assert _topic_match("rgv/#", "rgv/DEV1/ota/result")
    assert not _topic_match("rgv/DEV1/#", "rgv/DEV2/x")


def test_inmemory_transport_routing():
    tr = InMemoryTransport()
    received = []
    tr.subscribe("rgv/DEV1/ota/progress", lambda t, p: received.append((t, p)))
    tr.start()
    tr.publish("rgv/DEV1/ota/progress", b'{"a":1}')
    assert len(received) == 1
    assert json.loads(received[0][1]) == {"a": 1}


def test_inmemory_wildcard_and_log():
    tr = InMemoryTransport()
    hits = []
    tr.subscribe("rgv/+/ota/#", lambda t, p: hits.append(t))
    tr.device_publish("rgv/DEV1/ota/result", b'{"ota_result":"ok"}')
    assert len(hits) == 1
    # sent_log 记录方向
    assert tr.sent_log()[-1][0] == "pub"
    assert tr.sent_log()[-1][1].endswith("ota/result")
