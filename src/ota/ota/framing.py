"""固件包封帧：header（版本 + 长度 + 类型）+ payload + SHA256 + 签名。

格式（小端）
--------
  magic  : 4B   = b'XLOT'
  version: u32   单调递增整数序号
  ftype  : u8    见 config.FW_TYPES
  length : u32   payload 字节数
  payload: length B
  sha256 : 32B   payload 的 SHA256（整包完整性）
  signature: 32B HMAC-SHA256（header+payload，固件包真实性）

R-签名/完整性校验：unpack 时强制校验长度、SHA256、签名，任一失败抛 FramingError。
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Union

from . import config
from .crypto import sha256, sign, verify_signature
from .exceptions import FramingError

_HEADER_FMT = "<4sIBI"   # magic, version, ftype, length
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)
_SIG_SIZE = 32
_SHA_SIZE = 32


@dataclass(frozen=True)
class FirmwarePackage:
    version: int
    ftype: int
    payload: bytes
    sha256: bytes
    signature: bytes
    blob: bytes

    @property
    def size(self) -> int:
        return len(self.blob)


def _build_header(version: int, ftype: int, length: int) -> bytes:
    if version < 0:
        raise FramingError("版本序号不可为负")
    if ftype not in config.FW_TYPES:
        raise FramingError(f"非法固件类型: {ftype}")
    if length < 0 or length > config.PARTITION_CAPACITY:
        raise FramingError(f"payload 长度越界: {length}")
    return struct.pack(_HEADER_FMT, config.MAGIC_PACKAGE, version, ftype, length)


def pack_package(
    version: Union[int, str],
    ftype: int,
    payload: bytes,
    key: bytes,
) -> FirmwarePackage:
    """封帧并签名。version 接受整数或十进制字符串（单调序号）。"""
    from .versioning import parse_version

    ver = parse_version(version)
    header = _build_header(ver, ftype, len(payload))
    sha = sha256(payload)
    sig = sign(header + payload, key)
    blob = header + payload + sha + sig
    return FirmwarePackage(
        version=ver, ftype=ftype, payload=bytes(payload),
        sha256=sha, signature=sig, blob=blob,
    )


def unpack_package(blob: bytes, key: bytes) -> FirmwarePackage:
    """解析并校验（魔数 / 长度 / SHA256 / 签名）。失败抛 FramingError。"""
    if blob is None or len(blob) < _HEADER_SIZE + _SHA_SIZE + _SIG_SIZE:
        raise FramingError("固件包过短")
    magic, version, ftype, length = struct.unpack(_HEADER_FMT, blob[:_HEADER_SIZE])
    if magic != config.MAGIC_PACKAGE:
        raise FramingError(f"魔数错误: {magic!r}")
    expected = _HEADER_SIZE + length + _SHA_SIZE + _SIG_SIZE
    if len(blob) != expected:
        raise FramingError(f"长度不符: 实际 {len(blob)} 期望 {expected}")
    payload = blob[_HEADER_SIZE:_HEADER_SIZE + length]
    sha = blob[_HEADER_SIZE + length:_HEADER_SIZE + length + _SHA_SIZE]
    sig = blob[_HEADER_SIZE + length + _SHA_SIZE:_HEADER_SIZE + length + _SHA_SIZE + _SIG_SIZE]
    if sha != sha256(payload):
        raise FramingError("SHA256 校验失败（整包完整性）")
    if not verify_signature(sig, blob[:_HEADER_SIZE + length], key):
        raise FramingError("签名校验失败（固件包真实性）")
    return FirmwarePackage(
        version=version, ftype=ftype, payload=payload,
        sha256=sha, signature=sig, blob=blob,
    )
