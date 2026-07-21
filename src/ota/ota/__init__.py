"""XLPS2-Alpha 云端 OTA 服务（全新开发基线，不复用历史验证基线代码）。

模块职责
----------
- config        : 从 SSOT（config/mqtt_topics.json、ADR-005/006）派生的常量
- crypto        : CRC32 / SHA256 / HMAC 签名校验
- versioning    : 版本单调（单调递增整数，R4）
- framing       : 固件包封帧（header + SHA256 + 签名）
- chunking      : 分片（seq + CRC32）与断点续传（R-断电续传）
- flash         : STM32 内部 Flash 分区抽象（含内存实现，供单测）
- flag          : FLAG 扇区双备份（主 0x000 / 备 0x200，各 CRC-32），自愈（R15）
- ab_orchestrator : A/B 双分区状态机与回滚编排（R5 / R7）
- health_monitor  : 健康观测窗（HEALTH_WINDOW_S）确认与超时
- topics        : MQTT 主题构造/解析（rgv/{devId}/{topic}）
- mqtt_adapter  : MQTT 传输抽象 + 内存实现（离线单测用）
- mqtt_client   : EMQX TLS 客户端（paho，断线重连 + LWT）
- store         : 固件仓库（版本单调）
- schema        : 载荷校验（传输专有字段不污染 33 字段字典，ADR-006）
- service       : OTA 服务（cmd/data/progress/result 全流程编排）
"""

from . import config
from .versioning import Version, parse_version, is_newer, assert_monotonic
from .framing import FirmwarePackage, pack_package, unpack_package
from .chunking import Chunk, chunk_package, reassemble, resume_plan
from .flag import FlagRecord, FlagStore, FlagCorruptionError
from .flash import Flash, InMemoryFlash
from .ab_orchestrator import (
    DeviceAbState,
    UpgradePlan,
    AbOrchestrator,
    PendingAction,
)
from .health_monitor import HealthWindow, HealthStatus
from .store import FirmwareStore, FirmwareMeta
from .schema import (
    SchemaError,
    validate_ota_cmd,
    validate_ota_data,
    validate_ota_progress,
    validate_ota_result,
    encode_current_state,
    decode_current_state,
    CURRENT_STATE_SENTINEL,
)
from .service import OtaService, OtaJob, OtaJobStatus

__all__ = [
    "config",
    "Version", "parse_version", "is_newer", "assert_monotonic",
    "FirmwarePackage", "pack_package", "unpack_package",
    "Chunk", "chunk_package", "reassemble", "resume_plan",
    "FlagRecord", "FlagStore", "FlagCorruptionError",
    "Flash", "InMemoryFlash",
    "DeviceAbState", "UpgradePlan", "AbOrchestrator", "PendingAction",
    "HealthWindow", "HealthStatus",
    "FirmwareStore", "FirmwareMeta",
    "SchemaError", "validate_ota_cmd", "validate_ota_data",
    "validate_ota_progress", "validate_ota_result",
    "encode_current_state", "decode_current_state", "CURRENT_STATE_SENTINEL",
    "OtaService", "OtaJob", "OtaJobStatus",
]
