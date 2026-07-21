"""pytest 配置：将 src/ota 加入路径，使 `import ota` 可用（无需 pip install -e）。"""
import sys
from pathlib import Path

import pytest

SRC_OTA = str(Path(__file__).resolve().parent.parent)
if SRC_OTA not in sys.path:
    sys.path.insert(0, SRC_OTA)


@pytest.fixture
def key() -> bytes:
    """测试用 HMAC 签名密钥（32 字节）。"""
    return b"0123456789abcdef0123456789abcdef"
