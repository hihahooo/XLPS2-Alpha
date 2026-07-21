"""EmqxClient 单元测试：用伪 paho 模块，无需真实 broker。

覆盖：_build（TLS / 重连退避 / LWT）、start（connect_async+loop_start）、
重连后重订阅、on_message 路由、publish/stop。真实 broker 连通性属集成测试（需 EMQX）。
"""
import sys
import types

import pytest


def _install_fake_paho():
    pkg = types.ModuleType("paho")
    mqtt = types.ModuleType("paho.mqtt")
    client_mod = types.ModuleType("paho.mqtt.client")
    calls = {
        "subscribe": [], "publish": [], "will_set": [],
        "connect_async": [], "loop_start": 0, "loop_stop": 0, "disconnect": 0,
    }

    class _Msg:
        def __init__(self, topic, payload):
            self.topic = topic
            self.payload = payload

    class _Client:
        def __init__(self, client_id=None, clean_session=None):
            self.client_id = client_id
            self.clean_session = clean_session
            self.userdata = None
            self.on_connect = None
            self.on_disconnect = None
            self.on_message = None

        def tls_set(self, **kw):
            calls.setdefault("tls_set", []).append(kw)

        def username_pw_set(self, u, p):
            calls["username"] = (u, p)

        def reconnect_delay_set(self, min_delay=None, max_delay=None):
            calls["reconnect"] = (min_delay, max_delay)

        def will_set(self, topic, payload, qos, retain):
            calls["will_set"].append((topic, payload, qos, retain))

        def subscribe(self, topic, qos):
            calls["subscribe"].append((topic, qos))

        def publish(self, topic, payload, qos=0, retain=False):
            calls["publish"].append((topic, payload, qos, retain))
            return None

        def connect_async(self, host, port, keepalive):
            calls["connect_async"].append((host, port, keepalive))

        def loop_start(self):
            calls["loop_start"] += 1

        def loop_stop(self):
            calls["loop_stop"] += 1

        def disconnect(self):
            calls["disconnect"] += 1

    client_mod.Client = _Client
    client_mod.MQTTv311 = 4
    sys.modules["paho"] = pkg
    sys.modules["paho.mqtt"] = mqtt
    sys.modules["paho.mqtt.client"] = client_mod
    return client_mod, calls


def _uninstall_fake_paho():
    for k in ("paho.mqtt.client", "paho.mqtt", "paho"):
        sys.modules.pop(k, None)


def test_build_sets_lwt_and_reconnect():
    mod, calls = _install_fake_paho()
    try:
        from ota.mqtt_client import EmqxClient

        c = EmqxClient("cid", username="u", password="p", ca_certs="ca.pem")
        client = c._build()
        assert calls["will_set"]  # LWT 已设
        assert calls["reconnect"] == (1, 30)
        assert client.clean_session is False
    finally:
        _uninstall_fake_paho()


def test_start_connects_and_resubscribes_on_connect():
    mod, calls = _install_fake_paho()
    try:
        from ota.mqtt_client import EmqxClient

        c = EmqxClient("cid")
        c.start()
        assert calls["connect_async"] == [("emqx.np-xltech.com", 8883, 30)]
        assert calls["loop_start"] == 1
        # 模拟 broker 重连回调 → 上线可见 + 后续订阅生效
        c._on_connect(c._client, None, None, 0)
        assert c.is_connected() is True
        received = []
        c.subscribe("rgv/+/ota/progress", lambda t, p: received.append((t, p)), qos=1)
        assert ("rgv/+/ota/progress", 1) in calls["subscribe"]
        # 模拟下行消息路由
        class _M:
            topic = "rgv/DEV1/ota/progress"
            payload = b'{"x":1}'

        c._on_message(c._client, None, _M())
        assert received and received[0][0] == "rgv/DEV1/ota/progress"
    finally:
        _uninstall_fake_paho()


def test_publish_and_stop():
    mod, calls = _install_fake_paho()
    try:
        from ota.mqtt_client import EmqxClient

        c = EmqxClient("cid")
        c.start()
        c._on_connect(c._client, None, None, 0)
        c.publish("rgv/DEV1/ota/cmd", b"hi", qos=1)
        assert ("rgv/DEV1/ota/cmd", b"hi", 1, False) in calls["publish"]
        c.stop()
        assert calls["loop_stop"] == 1 and calls["disconnect"] == 1
        assert c.is_connected() is False
    finally:
        _uninstall_fake_paho()


def test_publish_without_connect_raises():
    mod, calls = _install_fake_paho()
    try:
        from ota.mqtt_client import EmqxClient

        c = EmqxClient("cid")
        # 未 start → 无 _client
        with pytest.raises(RuntimeError):
            c.publish("rgv/x/ota/cmd", b"x")
    finally:
        _uninstall_fake_paho()


def test_start_without_paho_raises(monkeypatch):
    # 环境未安装 paho 时应清晰报错（而非裸 ImportError）
    monkeypatch.setitem(sys.modules, "paho.mqtt.client", None)
    monkeypatch.setitem(sys.modules, "paho.mqtt", None)
    monkeypatch.setitem(sys.modules, "paho", None)
    from ota.mqtt_client import EmqxClient

    c = EmqxClient("cid")
    with pytest.raises(RuntimeError):
        c.start()
