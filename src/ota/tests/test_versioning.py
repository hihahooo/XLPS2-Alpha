"""版本单调（R4）单元测试。"""
import pytest

from ota.exceptions import VersionMonotonicError
from ota.versioning import Version, assert_monotonic, is_newer, parse_version


def test_parse_int():
    assert parse_version(1024) == 1024
    assert parse_version("1024") == 1024


def test_parse_rejects_nondecimal():
    with pytest.raises(ValueError):
        parse_version("1.2.3")  # semver 不参与单调比较
    with pytest.raises(ValueError):
        parse_version("abc")
    with pytest.raises(ValueError):
        parse_version(-1)
    with pytest.raises(ValueError):
        parse_version(True)  # bool 是 int 子类，显式拒绝
    with pytest.raises(ValueError):
        parse_version(None)


def test_is_newer():
    assert is_newer(1025, 1024)
    assert not is_newer(1024, 1024)
    assert not is_newer(1023, 1024)
    assert is_newer(1, None)  # 首次永远更新


def test_assert_monotonic_ok():
    assert assert_monotonic(1025, 1024) == 1025


@pytest.mark.parametrize("candidate,current", [(1024, 1024), (1023, 1024)])
def test_assert_monotonic_rejects_equal_or_lower(candidate, current):
    with pytest.raises(VersionMonotonicError):
        assert_monotonic(candidate, current)


def test_assert_monotonic_first_is_ok():
    assert assert_monotonic(1, None) == 1


def test_version_value_object():
    v = Version(1024, label="1.0.0")
    assert v.string == "1024"
    assert v > Version(1023)
    assert v >= Version(1024)
    assert v == Version(1024)
    assert Version(1024) == Version(1024)


def test_version_post_init_validates():
    with pytest.raises(ValueError):
        Version("bad")
