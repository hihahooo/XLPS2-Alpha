"""Flash 物理分区抽象。

云端 OTA 服务本身不直接擦写设备 Flash；此处抽象用于：
1. 在单测中以 ``InMemoryFlash`` 精确模拟 GD25Q127 ×2 双芯片物理分区行为；
2. 为设备端 OTA 客户端（CFW，L5 配置运维层）提供可移植的接口契约参考。

GD25Q127：16MB/芯片，4KB 扇区（0x1000），页 256B。本项目用双芯片做 A/B
物理双分区（ADR-005）。
"""
from __future__ import annotations

import abc
from typing import Dict, List

from . import config


class Flash(abc.ABC):
    """Flash 读写擦抽象。偏移为绝对地址。"""

    @abc.abstractmethod
    def read(self, offset: int, size: int) -> bytes:
        ...

    @abc.abstractmethod
    def write(self, offset: int, data: bytes) -> None:
        """写入（调用方须保证目标区域已擦除或允许覆盖）。"""

    @abc.abstractmethod
    def sector_erase(self, offset: int) -> None:
        """擦除 offset 所在扇区（4KB 对齐）。"""

    @abc.abstractmethod
    def size(self) -> int:
        ...


class InMemoryFlash(Flash):
    """内存 Flash 实现，用于单元测试与仿真。

    初始全 0xFF（与真实 NOR Flash 擦除态一致），写操作按位与（模拟写入 0 无法
    置 1，须先擦除），未擦除区写入会抛 ``ValueError`` 以暴露逻辑错误。

    地址空间按 ``base`` 窗口映射（默认 STM32 内部 Flash 窗口 0x08000000，容量 2MB），
    覆盖 A/B 分区与 FLAG(0x081E0000)。缓冲区按需增长，避免预分配整窗。
    """

    def __init__(self, capacity: int = 0x00200000, base: int = 0x08000000) -> None:
        self._cap = capacity
        self._base = base
        self._data = bytearray()

    # -- 内部辅助 ----------------------------------------------------------
    def _to_rel(self, offset: int) -> int:
        if offset < self._base:
            raise ValueError(f"越界访问 offset=0x{offset:x} < base=0x{self._base:x}")
        rel = offset - self._base
        return rel

    def _grow(self, rel_end: int) -> None:
        if rel_end > len(self._data):
            self._data.extend(b"\xff" * (rel_end - len(self._data)))

    def _check(self, offset: int, size: int) -> None:
        rel = self._to_rel(offset)
        if rel + size > self._cap:
            raise ValueError(
                f"越界访问 offset=0x{offset:x} size={size} "
                f"窗口 cap=0x{self._base + self._cap:x}"
            )

    # -- 公共接口 ----------------------------------------------------------
    def read(self, offset: int, size: int) -> bytes:
        rel = self._to_rel(offset)
        self._check(offset, size)
        self._grow(rel + size)
        return bytes(self._data[rel : rel + size])

    def write(self, offset: int, data: bytes) -> None:
        rel = self._to_rel(offset)
        self._check(offset, len(data))
        self._grow(rel + len(data))
        for i, b in enumerate(data):
            idx = rel + i
            # 模拟 NOR：只能将 1 写为 0；若目标位为 0 且要写 1 则视为未擦除错误
            if (self._data[idx] & b) != b:
                raise ValueError(
                    f"写入未擦除区域 @0x{offset + i:x}: 现有 0x{self._data[idx]:02x} "
                    f"目标 0x{b:02x}。须先 sector_erase"
                )
            self._data[idx] = b

    def sector_erase(self, offset: int) -> None:
        rel = self._to_rel(offset)
        if offset % config.FLAG_SECTOR_SIZE != 0:
            raise ValueError(f"扇区擦除须 4KB 对齐，收到 0x{offset:x}")
        self._check(offset, config.FLAG_SECTOR_SIZE)
        self._grow(rel + config.FLAG_SECTOR_SIZE)
        for i in range(config.FLAG_SECTOR_SIZE):
            self._data[rel + i] = 0xFF

    def size(self) -> int:
        return self._cap

    # -- 测试辅助 ----------------------------------------------------------
    def load_bin(self, offset: int, data: bytes) -> None:
        rel = self._to_rel(offset)
        self._check(offset, len(data))
        self._grow(rel + len(data))
        self._data[rel : rel + len(data)] = data

    def hexdump(self, offset: int, size: int) -> str:
        rel = self._to_rel(offset)
        self._check(offset, size)
        self._grow(rel + size)
        lines: List[str] = []
        for i in range(0, size, 16):
            chunk = self._data[rel + i : rel + i + 16]
            hexs = " ".join(f"{b:02x}" for b in chunk)
            lines.append(f"{offset + i:08x}  {hexs}")
        return "\n".join(lines)
