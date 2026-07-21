"""EMQX MQTT 客户端（真实运行用）。

- TLS（mqtts://emqx.np-xltech.com:8883，ADR-005）。
- 断线自动重连（paho 内置指数退避）+ 重连后重订阅。
- LWT（遗嘱）：云端离线时发布 ``rgv/cloud/status`` retain=false，供设备/运维感知。
- paho 仅在使用时延迟导入；未安装时 ``start()`` 抛清晰错误，不影响单测（单测用 InMemoryTransport）。

本类实现 ``MqttTransport`` 接口，因此 ``OtaService`` 无需感知底层是内存还是 EMQX。
"""
from __future__ import annotations

import json
import ssl
import threading
from typing import Callable, Dict, List, Optional, Tuple

from . import config
from .mqtt_adapter import MqttTransport, _topic_match

MessageCallback = Callable[[str, bytes], None]


class EmqxClient(MqttTransport):
    def __init__(
        self,
        client_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ca_certs: Optional[str] = None,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        host: str = config.EMQX_HOST,
        port: int = config.EMQX_PORT,
        keepalive: int = config.EMQX_KEEPALIVE_S,
    ) -> None:
        self._host = host
        self._port = port
        self._keepalive = keepalive
        self._client_id = client_id
        self._username = username
        self._password = password
        self._tls = {"ca_certs": ca_certs, "certfile": certfile, "keyfile": keyfile}
        self._subs: Dict[str, List[Tuple[MessageCallback, int]]] = {}
        self._connected = False
        self._client = None  # type: ignore[var-annotated]
        self._lock = threading.RLock()

    # -- 构建（延迟导入 paho）---------------------------------------
    def _build(self):
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError as e:  # 未安装 → 清晰报错
            raise RuntimeError(
                "运行 OTA 服务需 paho-mqtt（pip install paho-mqtt）。"
                "单元测试请使用 ota.mqtt_adapter.InMemoryTransport，无需 broker。"
            ) from e
        c = mqtt.Client(client_id=self._client_id, clean_session=False)
        tls_kwargs = {k: v for k, v in self._tls.items() if v is not None}
        if tls_kwargs:
            c.tls_set(
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
                **tls_kwargs,
            )
        else:
            # 至少启用 TLS 但不校验（生产应配 ca_certs）
            c.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
        if self._username:
            c.username_pw_set(self._username, self._password)
        # 自动重连退避
        c.reconnect_delay_set(min_delay=1, max_delay=30)
        # LWT：云端离线可见
        c.will_set(
            "rgv/cloud/status",
            json.dumps({"online": False, "ts": 0}).encode("utf-8"),
            qos=1, retain=False,
        )
        c.on_connect = self._on_connect
        c.on_disconnect = self._on_disconnect
        c.on_message = self._on_message
        return c

    # -- 回调 --------------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc):  # type: ignore[no-untyped-def]
        self._connected = True
        # 重连后重订阅（保险）
        for topic, cbs in self._subs.items():
            qos = max((q for _, q in cbs), default=1)
            client.subscribe(topic, qos)
        # 上线可见
        client.publish(
            "rgv/cloud/status",
            json.dumps({"online": True}).encode("utf-8"), qos=1, retain=False,
        )

    def _on_disconnect(self, client, userdata, rc):  # type: ignore[no-untyped-def]
        self._connected = False

    def _on_message(self, client, userdata, msg):  # type: ignore[no-untyped-def]
        topic = msg.topic
        payload = bytes(msg.payload)
        with self._lock:
            subs = list(self._subs.items())
        for pat, cbs in subs:
            if _topic_match(pat, topic):
                for cb, _ in cbs:
                    try:
                        cb(topic, payload)
                    except Exception:
                        import traceback

                        traceback.print_exc()

    # -- 接口实现 ----------------------------------------------------
    def subscribe(self, topic: str, callback: MessageCallback, qos: int = 1) -> None:
        with self._lock:
            self._subs.setdefault(topic, []).append((callback, qos))
        if self._connected and self._client is not None:
            self._client.subscribe(topic, qos)

    def publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        if self._client is None or not self._connected:
            raise RuntimeError("EMQX 未连接，无法发布；请先 start()")
        self._client.publish(topic, payload, qos=qos)

    def start(self) -> None:
        if self._client is None:
            self._client = self._build()
        self._client.connect_async(self._host, self._port, self._keepalive)
        self._client.loop_start()

    def stop(self) -> None:
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected
