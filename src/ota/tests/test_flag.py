"""FLAG 双备份自愈（R15 异常隔离）单元测试。"""
import pytest

from ota import config
from ota.exceptions import FlagCorruptionError
from ota.flag import FlagRecord, FlagStore
from ota.flash import InMemoryFlash


def _rec(active="A", committed="A", pending=False, target=0, deadline=0):
    return FlagRecord(
        active_slot=active, committed_slot=committed, pending=pending,
        target_version=target, health_deadline=deadline,
    )


def test_record_roundtrip():
    r = _rec("B", "A", True, 1024, 1300)
    assert FlagRecord.decode(r.encode()) == r


def test_decode_rejects_bad_crc():
    r = _rec()
    raw = bytearray(r.encode())
    raw[-1] ^= 0xFF  # 破坏 CRC
    assert FlagRecord.decode(bytes(raw)) is None


def test_flagstore_roundtrip():
    flash = InMemoryFlash()
    fs = FlagStore(flash)
    r = _rec("B", "A", True, 1024, 1300)
    fs.write(r)
    assert fs.read() == r


def test_primary_corruption_heals_from_backup():
    flash = InMemoryFlash()
    fs = FlagStore(flash)
    r = _rec("B", "A", True, 1024, 1300)
    fs.write(r)
    fs.corrupt_primary()  # 仅主备份损坏
    assert fs.read() == r  # 自愈自备


def test_both_corrupt_raises_unless_default():
    flash = InMemoryFlash()
    fs = FlagStore(flash)
    r = _rec()
    fs.write(r)
    # 双损：直接破坏两份
    raw = bytearray(r.encode())
    raw[0] ^= 0xFF
    flash.sector_erase(config.FLAG_SECTOR)
    flash.write(config.FLAG_SECTOR + config.FLAG_PRIMARY_OFFSET, bytes(raw))
    flash.write(config.FLAG_SECTOR + config.FLAG_BACKUP_OFFSET, bytes(raw))
    with pytest.raises(FlagCorruptionError):
        fs.read()
    # 安全回退：返回出厂默认（不抛）
    d = fs.read_default_or_existing()
    assert d.active_slot == config.SLOT_A
    assert d.pending is False


def test_record_validation():
    with pytest.raises(ValueError):
        FlagRecord(active_slot="X", committed_slot="A", pending=False, target_version=1)
    with pytest.raises(ValueError):
        FlagRecord(active_slot="A", committed_slot="B", pending=False, target_version=-1)
