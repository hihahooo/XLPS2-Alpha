"""MQTT 主题构造与解析（对齐 config/mqtt_topics.json）。

契约要点
--------
- 主题路径 ``rgv/{devId}/{topic}``，**devId 由路径承载，不进入 payload**（ADR-002/治理）。
- 10 个主题见 mqtt_topics.json；OTA 使用其中 4 个：
  ota/cmd(cloud→device)、ota/data(cloud→device)、
  ota/progress(device→cloud)、ota/result(device→cloud)。
"""
from __future__ import annotations

from typing import List, Tuple

from . import config


def build_topic(dev_id: str, topic: str) -> str:
    """构造完整主题 ``rgv/{devId}/{topic}``。"""
    if not dev_id:
        raise ValueError("devId 不可为空")
    if not topic:
        raise ValueError("topic 不可为空")
    if "/" in dev_id:
        raise ValueError("devId 不得含 '/'（须由路径承载）")
    return config.TOPIC_PATTERN.format(devId=dev_id, topic=topic)


def parse_topic(full: str) -> Tuple[str, str]:
    """解析 ``rgv/{devId}/{topic}`` → (devId, topic)。失败抛 ValueError。"""
    parts = full.split("/")
    # rgv / devId / ...topic（topic 本身不含 '/')
    if len(parts) < 3 or parts[0] != "rgv":
        raise ValueError(f"非法主题路径: {full!r}")
    dev_id = parts[1]
    topic = "/".join(parts[2:])
    if not dev_id or not topic:
        raise ValueError(f"非法主题路径: {full!r}")
    return dev_id, topic


def ota_topics(dev_id: str) -> dict:
    """返回某设备的 4 个 OTA 完整主题。"""
    return {
        "cmd": build_topic(dev_id, config.TOPIC_OTA_CMD),
        "data": build_topic(dev_id, config.TOPIC_OTA_DATA),
        "progress": build_topic(dev_id, config.TOPIC_OTA_PROGRESS),
        "result": build_topic(dev_id, config.TOPIC_OTA_RESULT),
    }


def is_ota_topic(topic: str) -> bool:
    try:
        _, rel = parse_topic(topic)
    except ValueError:
        return False
    return rel in {
        config.TOPIC_OTA_CMD,
        config.TOPIC_OTA_DATA,
        config.TOPIC_OTA_PROGRESS,
        config.TOPIC_OTA_RESULT,
    }


def all_topic_relpaths() -> List[str]:
    """从 SSOT 配置读出全部 10 个相对主题（校验：数量=10）。"""
    cfg = config.load_topics_config()
    topics = [t["topic"] for t in cfg["topics"]]
    assert len(topics) == config_load_topic_count(), "主题数量与 SSOT 不符"
    return topics


def config_load_topic_count() -> int:
    return 10
