"""分片传输与断点续传（R-断电续传）。

- 固件包按 CHUNK_SIZE 切片，每片带 ``seq``（从 0 起）与 ``crc``（CRC32）。
- 设备端可按 seq 重组；云端可依已收 seq 集合计算续传计划（缺失分片）。
- 分片为传输专有载荷，字段（seq/crc/chunk）不进入 33 字段字典（ADR-006）。
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from . import config
from .crypto import crc32
from .exceptions import ChunkIntegrityError


@dataclass(frozen=True)
class Chunk:
    seq: int
    crc: int
    data: bytes

    def to_dict(self) -> Dict[str, object]:
        """序列化为 MQTT 载荷（chunk 以 base64 承载，避免二进制破坏 JSON）。"""
        return {
            "seq": self.seq,
            "crc": self.crc,
            "chunk": base64.b64encode(self.data).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, object]) -> "Chunk":
        data = base64.b64decode(d["chunk"])  # type: ignore[arg-type]
        return cls(seq=int(d["seq"]), crc=int(d["crc"]), data=data)


def chunk_package(payload: bytes, chunk_size: int = config.CHUNK_SIZE) -> List[Chunk]:
    """将 payload 切分为带 seq/crc 的分片。空 payload 返回空列表。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正")
    if not payload:
        return []
    chunks: List[Chunk] = []
    for i in range(0, len(payload), chunk_size):
        piece = payload[i : i + chunk_size]
        chunks.append(Chunk(seq=len(chunks), crc=crc32(piece), data=piece))
    return chunks


def _validate_continuity(chunks: List[Chunk], total: Optional[int] = None) -> None:
    """校验 seq 连续 0..n-1 且无重复 / 无空洞。

    ``total`` 为分片总数（来自分片信封）。给定 total 才能判定「缺失」；
    若省略则仅校验已收分片自身连续（无重复 / 无内部空洞）。
    """
    seen: Set[int] = set()
    for c in chunks:
        if c.seq in seen:
            raise ChunkIntegrityError(f"重复分片 seq={c.seq}")
        seen.add(c.seq)
    n = total if total is not None else len(chunks)
    for seq in range(n):
        if seq not in seen:
            raise ChunkIntegrityError(f"缺失分片 seq={seq}")


def reassemble(chunks: List[Chunk], total: Optional[int] = None) -> bytes:
    """重组分片为原始 payload，逐片校验 CRC32 与序列连续性。

    ``total`` 为分片总数（来自分片信封）；省略时仅校验已收分片自身连续。
    """
    if not chunks:
        return b""
    ordered = sorted(chunks, key=lambda c: c.seq)
    _validate_continuity(ordered, total)
    out = bytearray()
    for c in ordered:
        if crc32(c.data) != c.crc:
            raise ChunkIntegrityError(f"分片 CRC 校验失败 seq={c.seq}")
        out += c.data
    return bytes(out)


def resume_plan(total: int, received: Iterable[int]) -> List[int]:
    """计算续传缺失分片序号（升序）。total=总分片数。"""
    if total < 0:
        raise ValueError("total 不可为负")
    got: Set[int] = set()
    for s in received:
        s = int(s)
        if 0 <= s < total:
            got.add(s)
    return [i for i in range(total) if i not in got]


def chunks_to_payload(chunks: List[Chunk], *, total: int, ftype: int, version: object) -> bytes:
    """封装为 ota/data 的传输专有 JSON 载荷（不含 devId，devId 由 Topic 承载）。"""
    return json.dumps(
        {
            "total": total,
            "ftype": ftype,
            "version": str(version),
            "chunks": [c.to_dict() for c in chunks],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def payload_to_chunks(payload: bytes) -> List[Chunk]:
    obj = json.loads(payload.decode("utf-8"))
    return [Chunk.from_dict(c) for c in obj["chunks"]]
