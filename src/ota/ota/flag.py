"""FLAG 扇区双备份（主 0x000 / 备 0x200，各 CRC-32）—— R15 异常隔离。

设计
----
- FLAG 扇区记录当前激活分区、已提交分区、待切换目标版本、健康截止时间、pending 位。
- 主备两份完全一致，各自带 CRC-32，防止单点损坏。
- 读时优先主备份；主损坏则回退备备份（自愈）；双损则抛 ``FlagCorruptionError``。
- 写时先擦扇区再写主、再写备（任一成功即可恢复，双写保证可用性）。
- FLAG 内的 ``active_slot`` 是设备内部存储字段，**不进入 33 字段数据字典**（ADR-006）。
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

from . import config
from .crypto import crc32
from .exceptions import FlagCorruptionError
from .flash import Flash

_FLAG_FMT = "<4sBBBBBII"   # magic, schema, active, committed, pending, ftype, version, health_deadline
_FLAG_FIXED = struct.calcsize(_FLAG_FMT)  # 不含尾部 CRC
_FLAG_TOTAL = _FLAG_FIXED + 4             # 含 CRC32


@dataclass(frozen=True)
class FlagRecord:
    """FLAG 扇区记录（设备内部，不进字典）。"""

    active_slot: str              # 'A' / 'B'
    committed_slot: str           # 已提交稳定分区
    pending: bool                 # 是否存在待确认的切换
    target_version: int           # 待切换目标版本序号（pending=False 时为当前版本）
    health_deadline: int = 0     # 健康观测窗截止 epoch 秒（0=无）
    ftype: int = config.FW_TYPE_FIRMWARE
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.active_slot not in config.SLOTS:
            raise ValueError(f"非法 active_slot: {self.active_slot!r}")
        if self.committed_slot not in config.SLOTS:
            raise ValueError(f"非法 committed_slot: {self.committed_slot!r}")
        if self.target_version < 0:
            raise ValueError("target_version 不可为负")
        if self.health_deadline < 0:
            raise ValueError("health_deadline 不可为负")

    # -- 二进制编解码 ------------------------------------------------------
    def encode(self) -> bytes:
        body = struct.pack(
            _FLAG_FMT,
            config.MAGIC_FLAG,
            self.schema_version,
            ord(self.active_slot),
            ord(self.committed_slot),
            1 if self.pending else 0,
            self.ftype,
            self.target_version,
            self.health_deadline,
        )
        return body + struct.pack("<I", crc32(body))

    @classmethod
    def decode(cls, raw: bytes) -> Optional["FlagRecord"]:
        if raw is None or len(raw) < _FLAG_TOTAL:
            return None
        body, crc = raw[:_FLAG_FIXED], raw[_FLAG_FIXED:_FLAG_TOTAL]
        if struct.unpack("<I", crc)[0] != crc32(body):
            return None  # CRC 不匹配 → 该备份损坏
        (
            magic, schema, active, committed, pending, ftype, version, deadline
        ) = struct.unpack(_FLAG_FMT, body)
        if magic != config.MAGIC_FLAG:
            return None
        return cls(
            active_slot=chr(active),
            committed_slot=chr(committed),
            pending=bool(pending),
            target_version=version,
            health_deadline=deadline,
            ftype=ftype,
            schema_version=schema,
        )


class FlagStore:
    """FLAG 扇区访问（双备份 + 自愈）。"""

    def __init__(self, flash: Flash, sector: int = config.FLAG_SECTOR) -> None:
        self._flash = flash
        self._sector = sector

    def _read_raw(self, offset: int) -> bytes:
        return self._flash.read(self._sector + offset, _FLAG_TOTAL)

    def read(self) -> FlagRecord:
        """读取并自愈：主 → 备 → 默认。双损抛 ``FlagCorruptionError``。"""
        primary = FlagRecord.decode(self._read_raw(config.FLAG_PRIMARY_OFFSET))
        if primary is not None:
            return primary
        backup = FlagRecord.decode(self._read_raw(config.FLAG_BACKUP_OFFSET))
        if backup is not None:
            return backup
        raise FlagCorruptionError("FLAG 主备双备份均损坏，无法自愈")

    def read_default_or_existing(self) -> FlagRecord:
        """读取；若无任何有效记录则返回出厂默认（A 激活，无 pending）。"""
        try:
            return self.read()
        except FlagCorruptionError:
            return FlagRecord(
                active_slot=config.SLOT_A,
                committed_slot=config.SLOT_A,
                pending=False,
                target_version=0,
            )

    def write(self, record: FlagRecord) -> None:
        """双写：擦扇区 → 写主 → 写备（各自独立可恢复）。"""
        raw = record.encode()
        self._flash.sector_erase(self._sector)
        self._flash.write(self._sector + config.FLAG_PRIMARY_OFFSET, raw)
        self._flash.write(self._sector + config.FLAG_BACKUP_OFFSET, raw)

    def corrupt_primary(self) -> None:
        """测试辅助：破坏主备份（模拟单点损坏），验证自愈。"""
        cur = self.read_default_or_existing()
        raw = bytearray(cur.encode())
        raw[0] ^= 0xFF  # 翻转魔数字节使其 CRC 失败
        self._flash.sector_erase(self._sector)
        self._flash.write(self._sector + config.FLAG_PRIMARY_OFFSET, bytes(raw))
        self._flash.write(self._sector + config.FLAG_BACKUP_OFFSET, cur.encode())
