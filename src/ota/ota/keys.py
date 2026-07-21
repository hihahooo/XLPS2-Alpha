"""签名密钥加载（生产由 KMS / 安全存储托管；此处从文件或环境变量读取）。"""
from __future__ import annotations

import os
from typing import Optional


def load_signing_key(path: Optional[str] = None) -> bytes:
    """加载 HMAC 签名密钥（hex 编码）。

    优先级：显式 path > 环境变量 ``XLPS2_OTA_KEY`` > 报错。
    禁止每次随机生成（会导致签名不一致）。
    """
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return bytes.fromhex(f.read().strip())
    env = os.environ.get("XLPS2_OTA_KEY")
    if env:
        return bytes.fromhex(env.strip())
    raise RuntimeError(
        "未提供签名密钥：请用 --key-file 指定（hex 文件），"
        "或导出环境变量 XLPS2_OTA_KEY=<hex>"
    )


def write_key_file(path: str, key: bytes) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(key.hex())
