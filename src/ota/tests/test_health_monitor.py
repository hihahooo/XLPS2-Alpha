"""健康观测窗（R7 健康确认与超时）单元测试。"""
import pytest

from ota.health_monitor import HealthStatus, HealthWindow


def test_open_and_report():
    w = HealthWindow(window_s=300)
    w.open(now=1000)
    assert w.deadline() == 1300
    assert w.report(now=1200) is True
    assert w.is_confirmed() is True
    assert w.status == HealthStatus.CONFIRMED


def test_expired_report_false():
    w = HealthWindow(window_s=300)
    w.open(now=1000)
    assert w.report(now=1400) is False  # 超时后回报无效
    assert w.is_expired(now=1400) is True
    assert w.is_expired(now=1299) is False


def test_remaining():
    w = HealthWindow(window_s=300)
    w.open(now=1000)
    assert w.remaining(now=1000) == 300
    assert w.remaining(now=1200) == 100
    assert w.remaining(now=2000) == 0


def test_status_idle_before_open():
    w = HealthWindow()
    assert w.status == HealthStatus.IDLE
    assert w.deadline() is None


def test_close_resets():
    w = HealthWindow(window_s=300)
    w.open(now=1000)
    w.report(now=1100)
    w.close()
    assert w.status == HealthStatus.IDLE
    assert w.deadline() is None
    assert w.is_confirmed() is False


def test_negative_now_rejected():
    w = HealthWindow()
    with pytest.raises(ValueError):
        w.open(now=-1)
