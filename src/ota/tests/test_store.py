"""固件仓库版本单调（R4）单元测试。"""
import pytest

from ota import config
from ota.exceptions import VersionMonotonicError
from ota.framing import pack_package
from ota.store import FirmwareStore


_KEY = b"k" * 32


def _pkg(version, payload=b"FW"):
    return pack_package(version, config.FW_TYPE_FIRMWARE, payload, _KEY)


def test_publish_and_query(tmp_path, key):
    st = FirmwareStore(str(tmp_path), signing_key=_KEY)
    meta = st.publish(_pkg(100, b"v100"))
    assert meta.version == 100
    assert st.latest() == 100
    assert st.has(100)
    assert st.versions() == [100]


def test_monotonic_enforced(tmp_path, key):
    st = FirmwareStore(str(tmp_path), signing_key=_KEY)
    st.publish(_pkg(100))
    with pytest.raises(VersionMonotonicError):
        st.publish(_pkg(50))    # 降级
    with pytest.raises(VersionMonotonicError):
        st.publish(_pkg(100))   # 平级
    st.publish(_pkg(101))       # 升级 OK
    assert st.latest() == 101


def test_get_verifies_signature(tmp_path, key):
    st = FirmwareStore(str(tmp_path), signing_key=_KEY)
    st.publish(_pkg(100, b"payload-bytes"))
    pkg = st.get(100)
    assert pkg.payload == b"payload-bytes"
    assert st.meta(100).sha256_hex == pkg.sha256.hex()


def test_get_blob_without_key(tmp_path):
    st = FirmwareStore(str(tmp_path))  # 无密钥
    st.publish(_pkg(100))
    blob = st.get_blob(100)
    assert isinstance(blob, bytes) and len(blob) > 0
    with pytest.raises(RuntimeError):
        st.get(100)  # 无密钥无法解包


def test_versions_sorted(tmp_path, key):
    st = FirmwareStore(str(tmp_path), signing_key=_KEY)
    for v in (100, 200, 300):  # 单调递增发布
        st.publish(_pkg(v))
    assert st.versions() == [100, 200, 300]
