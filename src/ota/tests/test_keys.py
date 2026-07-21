"""签名密钥加载单元测试。"""
import os

import pytest

from ota import keys


def test_load_from_file(tmp_path):
    p = str(tmp_path / "k.hex")
    keys.write_key_file(p, b"ab" * 16)
    assert keys.load_signing_key(p) == b"ab" * 16


def test_load_from_env(monkeypatch):
    monkeypatch.setenv("XLPS2_OTA_KEY", ("cd" * 32).encode().hex())
    assert keys.load_signing_key(None) == b"cd" * 32


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("XLPS2_OTA_KEY", raising=False)
    with pytest.raises(RuntimeError):
        keys.load_signing_key(None)
    with pytest.raises(FileNotFoundError):
        keys.load_signing_key("/no/such/key.hex")
