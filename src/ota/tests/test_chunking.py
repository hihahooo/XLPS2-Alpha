"""分片与断点续传（R-断电续传）单元测试。"""
import pytest

from ota import chunking as ck
from ota import config
from ota.exceptions import ChunkIntegrityError


def test_chunk_roundtrip():
    payload = b"XLPS2-RGV-OTA-" * 200  # > CHUNK_SIZE
    chunks = ck.chunk_package(payload, config.CHUNK_SIZE)
    assert len(chunks) == (len(payload) + config.CHUNK_SIZE - 1) // config.CHUNK_SIZE
    assert ck.reassemble(chunks) == payload


def test_chunk_seq_and_crc():
    payload = b"\x01\x02\x03" * 500
    chunks = ck.chunk_package(payload, 64)
    assert [c.seq for c in chunks] == list(range(len(chunks)))
    for c in chunks:
        assert c.crc == __import__("zlib").crc32(c.data) & 0xFFFFFFFF


def test_empty_payload():
    assert ck.chunk_package(b"", 1024) == []
    assert ck.reassemble([]) == b""


def test_crc_mismatch_raises():
    chunks = ck.chunk_package(b"hello world", 4)
    bad = [ck.Chunk(seq=c.seq, crc=c.crc ^ 0xFF, data=c.data) for c in chunks]
    with pytest.raises(ChunkIntegrityError):
        ck.reassemble(bad)


def test_duplicate_seq_raises():
    chunks = ck.chunk_package(b"abcdefgh", 4)
    with pytest.raises(ChunkIntegrityError):
        ck.reassemble(chunks + [chunks[0]])


def test_missing_seq_raises():
    chunks = ck.chunk_package(b"abcdefgh", 4)  # 2 片
    partial = chunks[:-1]  # 仅收到 seq0
    with pytest.raises(ChunkIntegrityError):
        ck.reassemble(partial, total=2)


def test_resume_plan():
    # 共 5 片，已收 0..2，缺 3,4
    missing = ck.resume_plan(5, [0, 1, 2])
    assert missing == [3, 4]
    # 已收全部
    assert ck.resume_plan(5, range(5)) == []
    # 乱序/越界忽略
    assert ck.resume_plan(3, [0, 5, -1]) == [1, 2]


def test_chunk_dict_roundtrip():
    chunks = ck.chunk_package(b"payload-data", 5)
    d = [c.to_dict() for c in chunks]
    back = [ck.Chunk.from_dict(x) for x in d]
    assert ck.reassemble(back) == b"payload-data"


def test_payload_envelope_roundtrip():
    payload = b"envelope-test" * 30
    chunks = ck.chunk_package(payload, config.CHUNK_SIZE)
    blob = ck.chunks_to_payload(chunks, total=len(chunks), ftype=config.FW_TYPE_FIRMWARE, version=1024)
    out = ck.payload_to_chunks(blob)
    assert ck.reassemble(out) == payload


def test_invalid_chunk_size():
    with pytest.raises(ValueError):
        ck.chunk_package(b"x", 0)
