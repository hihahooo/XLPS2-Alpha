#!/usr/bin/env python3
"""打包并发布固件 / SMDL / 参数包（版本单调 + 签名）。

用法
----
    python scripts/build_firmware.py <raw.bin> <version> \
        [--type 1|2|3] [--store-dir ./store/firmware] \
        [--key-file ./broker/ota_key.hex] [--note "..."]

- version 必须为单调递增整数序号（decimal string 承载于 SSOT string 字段）。
- 仓库已有更大版本时会拒绝（R4 双保险）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ota import config, framing, keys, store  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="打包并发布 OTA 包")
    ap.add_argument("bin", help="原始镜像文件（.bin / .smdl / .params）")
    ap.add_argument("version", help="单调递增整数序号")
    ap.add_argument("--type", type=int, default=config.FW_TYPE_FIRMWARE,
                    help="1=固件 2=SMDL 3=参数")
    ap.add_argument("--store-dir",
                    default=str(Path(__file__).resolve().parents[1] / "store" / "firmware"))
    ap.add_argument("--key-file", default=None)
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    key = keys.load_signing_key(args.key_file)
    data = open(args.bin, "rb").read()
    pkg = framing.pack_package(args.version, args.type, data, key)
    st = store.FirmwareStore(args.store_dir, signing_key=key)
    meta = st.publish(pkg, note=args.note)
    print(
        f"已发布：version={meta.version} ftype={meta.ftype} "
        f"size={meta.size}B sha256={meta.sha256_hex[:16]}… "
        f"仓库最新={st.latest()}"
    )


if __name__ == "__main__":
    main()
