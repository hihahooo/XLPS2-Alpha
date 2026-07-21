"""版本模型与单调校验（R4 版本单调）。

设计决策（待主理人确认）
------------------------
SSOT 的 data_dictionary.json 将 ``fw_version`` / ``ota_target_version`` 定义为
``string`` 类型；ADR-005 与 modules/ota.md 要求「版本号单调递增整数，严格拒绝
≤ 当前」。二者表面冲突。

本基线统一为：**单调递增序号（整数）以十进制字符串形式承载于上述 string 字段**，
即 ``"1024"`` 表示序号 1024。语义版本号（如 ``"1.2.3"``）仅作为展示别名，
不参与单调比较。所有单调递增判定只比较整数序号。这样既满足 SSOT 的 string 类型，
又满足「单调递增整数」的硬约束。

如有需要改为 semver 比较，须由主理人裁定并同步 ADR-005。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from .exceptions import VersionMonotonicError


def parse_version(version: Union[int, str]) -> int:
    """将版本解析为单调递增整数序号。

    接受整数或纯十进制数字字符串。非法输入抛 ``ValueError``。
    """
    if isinstance(version, bool):  # bool 是 int 子类，显式拒绝
        raise ValueError("版本不可为布尔值")
    if isinstance(version, int):
        if version < 0:
            raise ValueError("版本序号不可为负")
        return version
    if version is None:
        raise ValueError("版本不可为空")
    s = str(version).strip()
    if not s:
        raise ValueError("版本字符串不可为空")
    # 仅接受十进制整数字符串（不允许 semver 参与单调比较）
    if not s.isdigit():
        raise ValueError(f"版本须为十进制整数序号，收到: {version!r}")
    return int(s)


def is_newer(candidate: Union[int, str], current: Union[int, str, None]) -> bool:
    """candidate 是否严格大于 current。current 为 None 视为首次（永远是更新）。"""
    if current is None:
        return True
    return parse_version(candidate) > parse_version(current)


def assert_monotonic(candidate: Union[int, str], current: Union[int, str, None]) -> int:
    """R4 版本单调：candidate 必须严格大于 current，禁止降级/平级。

    返回候选的整数序号。违反则抛 ``VersionMonotonicError``。
    """
    cand = parse_version(candidate)
    if current is None:
        return cand
    cur = parse_version(current)
    if cand <= cur:
        raise VersionMonotonicError(
            f"版本非单调：candidate={cand} 必须严格大于 current={cur}"
            f"（禁止降级 / 平级回灌）"
        )
    return cand


@dataclass(frozen=True)
class Version:
    """版本值对象：整数序号 + 可选语义别名。"""

    ordinal: int
    label: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ordinal", parse_version(self.ordinal))

    @property
    def string(self) -> str:
        """承载于 SSOT string 字段的形式（十进制序号）。"""
        return str(self.ordinal)

    def __gt__(self, other: "Version") -> bool:
        return self.ordinal > other.ordinal

    def __ge__(self, other: "Version") -> bool:
        return self.ordinal >= other.ordinal

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self.ordinal == other.ordinal

    def __hash__(self) -> int:
        return hash(self.ordinal)

    def __repr__(self) -> str:
        if self.label:
            return f"Version({self.ordinal}, label={self.label!r})"
        return f"Version({self.ordinal})"
