"""MQTT 传输抽象 + 内存实现（离线单测 / 集成测试用）。

- ``MqttTransport``：云端 OTA 服务对所有 MQTT 操作的统一接口（订阅/发布/启停/连接态）。
- ``InMemoryTransport``：进程内路由，支持 ``+``/``#`` 通配，供单测与集成测试使用，
  无需真实 broker。真实 EMQX 客户端见 ``mqtt_client.EmqxClient``。
"""
from __future__ import annotations

import abc
import asyncio
import fnmatch
import threading
from typing import Callable, Dict, List, Optional, Tuple

# 回调签名：(topic: str, payload: bytes) -> None
MessageCallback = Callable[[str, bytes], None]


def _topic_match(pattern: str, topic: str) -> bool:
    """支持 MQTT 通配：``+`` 单层、``#`` 多层。"""
    if pattern == topic:
        return True
    pat_parts = pattern.split("/")
    sub_parts = topic.split("/")
    i = 0
    while i < len(pat_parts):
        p = pat_parts[i]
        if p == "#":
            return True
        if p == "+":
            if i >= len(sub_parts):
                return False
            i += 1
            continue
        if i >= len(sub_parts) or p != sub_parts[i]:
            return False
        i += 1
    return i == len(sub_parts)


class MqttTransport(abc.ABC):
    """云端 OTA 服务使用的 MQTT 操作接口。"""

    @abc.abstractmethod
    def subscribe(self, topic: str, callback: MessageCallback, qos: int = 1) -> None:
        ...

    @abc.abstractmethod
    def publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        ...

    @abc.abstractmethod
    def start(self) -> None:
        """连接 / 启动传输。"""

    @abc.abstractmethod
    def stop(self) -> None:
        ...

    @abc.abstractmethod
    def is_connected(self) -> bool:
        ...


class InMemoryTransport(MqttTransport):
    """进程内 MQTT 路由（单测 / 集成测试）。

    可用于在测试里注册一个「设备端」处理 cloud→device 消息并回发 progress/result，
    从而达成不依赖 broker 的端到端验证。
    """

    def __init__(self) -> None:
        self._subs: Dict[str, List[Tuple[MessageCallback, int]]] = {}
        self._connected = False
        self._lock = threading.RLock()
        self._log: List[Tuple[str, str, bytes]] = []  # (direction, topic, payload)

    # -- 服务端（OTA 服务）接口 -------------------------------------------
    def subscribe(self, topic: str, callback: MessageCallback, qos: int = 1) -> None:
        with self._lock:
            self._subs.setdefault(topic, []).append((callback, qos))

    def publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        with self._lock:
            self._log.append(("pub", topic, bytes(payload)))
            for pat, cbs in list(self._subs.items()):
                if _topic_match(pat, topic):
                    for cb, _ in cbs:
                        cb(topic, bytes(payload))

    def start(self) -> None:
        self._connected = True

    def stop(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    # -- 测试辅助：模拟设备端 -------------------------------------------
    def device_publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        """模拟设备端向云端发布（device→cloud）。"""
        self.publish(topic, payload, qos)

    def on_cloud_message(self, pattern: str, callback: MessageCallback, qos: int = 1) -> None:
        """测试用：注册一个「设备端」监听器，接收 cloud→device 消息。"""
        self.subscribe(pattern, callback, qos)

    def sent_log(self) -> List[Tuple[str, str, bytes]]:
        return list(self._log)

    def reset(self) -> None:
        with self._lock:
            self._subs.clear()
            self._log.clear()
