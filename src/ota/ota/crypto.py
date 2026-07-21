"""密码学工具：CRC32（分片完整性）、SHA256（整包完整性）、HMAC（签名/验签）。"""
from __future__ import annotations

import hashlib
import hmac
import os
import zlib
from typing import Union

BytesLike = Union[bytes, bytearray]


def crc32(data: BytesLike) -> int:
    """返回无符号 32 位 CRC32（分片级完整性）。"""
    return zlib.crc32(bytes(data)) & 0xFFFFFFFF


def sha256(data: BytesLike) -> bytes:
    """返回 32 字节 SHA256 摘要（整包完整性）。"""
    return hashlib.sha256(bytes(data)).digest()


def sha256_hex(data: BytesLike) -> str:
    return hashlib.sha256(bytes(data)).hexdigest()


def sign(payload: BytesLike, key: BytesLike) -> bytes:
    """HMAC-SHA256 签名（固件包真实性）。返回 32 字节。"""
    return hmac.new(bytes(key), bytes(payload), hashlib.sha256).digest()


def verify_signature(signature: BytesLike, payload: BytesLike, key: BytesLike) -> bool:
    """恒定时间验签。"""
    return hmac.compare_digest(hmac.new(bytes(key), bytes(payload), hashlib.sha256).digest(), bytes(signature))


def gen_key() -> bytes:
    """生成 32 字节随机签名密钥（生产由 KMS / 安全存储托管）。"""
    return os.urandom(32)
