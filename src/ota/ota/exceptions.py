"""OTA 异常层级。"""
from __future__ import annotations


class OtaError(Exception):
    """所有 OTA 错误的基类。"""


class VersionMonotonicError(OtaError):
    """R4 版本单调违规：新版本未严格大于当前。"""


class ChunkIntegrityError(OtaError):
    """分片 CRC 校验失败或序列不连续。"""


class FramingError(OtaError):
    """固件包封帧解析/签名校验失败。"""


class FlagCorruptionError(OtaError):
    """FLAG 扇区主备双备份均损坏，无法自愈。"""


class SlotError(OtaError):
    """非法槽位 / 分区选择错误。"""


class SchemaError(OtaError):
    """载荷违反 SSOT 数据字典 / 主题契约。"""


class HealthTimeoutError(OtaError):
    """健康观测窗超时，未收到设备健康确认。"""


class AbortError(OtaError):
    """升级被显式中止（设备上报 fail / 用户回滚）。"""
