"""固件包封帧 + 签名/完整性校验（R-签名/完整性）。"""
import pytest

from ota import config
from ota.exceptions import FramingError
from ota.framing import FirmwarePackage, pack_package, unpack_package, _HEADER_SIZE


def _roundtrip(key, version=1024, ftype=config.FW_TYPE_FIRMWARE, payload=b"HELLO-XLPS2"):
    pkg = pack_package(version, ftype, payload, key)
    assert isinstance(pkg, FirmwarePackage)
    out = unpack_package(pkg.blob, key)
    assert out.version == version
    assert out.payload == payload
    assert out.sha256 == pkg.sha256
    return pkg


def test_pack_unpack_roundtrip(key):
    _roundtrip(key)


def test_pack_unpack_large(key):
    _roundtrip(key, version=9999, payload=bytes(range(256)) * 10)


def test_tamper_payload_fails(key):
    pkg = _roundtrip(key)
    bad = bytearray(pkg.blob)
    bad[_HEADER_SIZE] ^= 0xFF  # 翻转 payload 首字节
    with pytest.raises(FramingError):
        unpack_package(bytes(bad), key)


def test_tamper_signature_fails(key):
    pkg = _roundtrip(key)
    bad = bytearray(pkg.blob)
    bad[-1] ^= 0xFF  # 翻转签名末字节
    with pytest.raises(FramingError):
        unpack_package(bytes(bad), key)


def test_wrong_magic_fails(key):
    pkg = _roundtrip(key)
    bad = bytearray(pkg.blob)
    bad[0] ^= 0xFF
    with pytest.raises(FramingError):
        unpack_package(bytes(bad), key)


def test_wrong_key_fails(key):
    pkg = _roundtrip(key)
    other = b"differentkey123456differentkey123456"
    with pytest.raises(FramingError):
        unpack_package(pkg.blob, other)


def test_length_mismatch_fails(key):
    pkg = _roundtrip(key)
    bad = pkg.blob + b"\x00"
    with pytest.raises(FramingError):
        unpack_package(bad, key)


def test_bad_ftype(key):
    with pytest.raises(FramingError):
        pack_package(1, 0x99, b"x", key)
