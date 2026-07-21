"""InMemoryFlash 行为（模拟 STM32H743 内部 Flash A/B 逻辑分区）。"""
import pytest

from ota import config
from ota.flash import InMemoryFlash


def test_read_write_erase():
    f = InMemoryFlash(base=0, capacity=0x2000)
    # 初始全 0xFF
    assert f.read(0, 4) == b"\xff\xff\xff\xff"
    f.sector_erase(0)
    f.write(0, b"\x01\x02\x03\x04")
    assert f.read(0, 4) == b"\x01\x02\x03\x04"


def test_write_without_erase_raises():
    # NOR 语义：0→1（置位）允许；1→0（清位，须先擦除）才报错。
    f = InMemoryFlash(base=0, capacity=0x2000)
    f.sector_erase(0)
    f.write(0, b"\x01")
    with pytest.raises(ValueError):
        f.write(0, b"\x02")  # 在已写 0x01 区清位，须先擦除


def test_sector_erase_alignment():
    f = InMemoryFlash(base=0, capacity=0x2000)
    with pytest.raises(ValueError):
        f.sector_erase(0x10)  # 非 4KB 对齐


def test_erase_clears():
    f = InMemoryFlash(base=0, capacity=0x2000)
    f.sector_erase(0)
    f.write(0, b"\xAB" * 8)
    f.sector_erase(0)
    assert f.read(0, 8) == b"\xff" * 8


def test_flash_geometry_constants():
    assert config.FLAG_SECTOR_SIZE == 0x1000
    assert config.PARTITION_CAPACITY == 0x0E0000


def test_hexdump_and_load_bin():
    f = InMemoryFlash(base=0, capacity=0x2000)
    f.sector_erase(0)
    f.write(0, b"ABCD")
    dump = f.hexdump(0, 4)
    assert "41 42 43 44" in dump  # 'A' 'B' 'C' 'D'
    f.load_bin(0x1000, b"Z")
    assert f.read(0x1000, 1) == b"Z"
