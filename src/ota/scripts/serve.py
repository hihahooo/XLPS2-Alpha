#!/usr/bin/env python3
"""运行 XLPS2-Alpha 云端 OTA 服务（真实 EMQX TLS 连接）。

用法
----
    python scripts/serve.py \
        --client-id xlps2-ota-cloud \
        --username <user> --password <pwd> \
        --ca-certs ./broker/ca.pem \
        --store-dir ./store/firmware \
        --key-file ./broker/ota_key.hex

订阅：rgv/+/ota/progress、rgv/+/ota/result、rgv/+/telemetry
（升级由 HMI/运维经其它通道触发，本服务被动响应设备回报并编排回滚）
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# 让脚本可直接运行（无需 pip install -e）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ota import config, keys, mqtt_client, service, store  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="XLPS2-Alpha 云端 OTA 服务")
    ap.add_argument("--client-id", default="xlps2-ota-cloud")
    ap.add_argument("--username", default=None)
    ap.add_argument("--password", default=None)
    ap.add_argument("--ca-certs", default=None)
    ap.add_argument("--store-dir", default=str(Path(__file__).resolve().parents[1] / "store" / "firmware"))
    ap.add_argument("--key-file", default=None)
    args = ap.parse_args()

    key = keys.load_signing_key(args.key_file)
    st = store.FirmwareStore(args.store_dir, signing_key=key)
    tr = mqtt_client.EmqxClient(
        client_id=args.client_id,
        username=args.username,
        password=args.password,
        ca_certs=args.ca_certs,
    )
    svc = service.OtaService(tr, st, key)

    def on_event(dev_id, etype, data):
        print(f"[ota-event] {dev_id} {etype} {data}", flush=True)

    svc._on_event = on_event
    svc.start()
    print(
        f"OTA 服务已启动（EMQX {config.EMQX_HOST}:{config.EMQX_PORT}）。"
        f"仓库当前最新版本={st.latest()}"
    )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止 OTA 服务…")
        svc.stop()


if __name__ == "__main__":
    main()
