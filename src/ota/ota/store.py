"""固件仓库（版本单调）。

- 每个版本落盘为 ``<version>.bin``（封帧 blob）+ ``<version>.meta.json``。
- 发布时强制单调：新版本须严格大于仓库内已有最大版本（R4 双保险，服务层也已校验）。
- 支持按版本取包（带签名校验）、列版本、取最新、断点续传所需的整包读取。
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from . import config
from .exceptions import VersionMonotonicError
from .framing import FirmwarePackage, unpack_package
from .versioning import is_newer, parse_version


@dataclass(frozen=True)
class FirmwareMeta:
    version: int
    ftype: int
    size: int
    sha256_hex: str
    created_at: float
    note: str = ""

    def as_dict(self) -> Dict[str, object]:
        return {
            "version": self.version,
            "ftype": self.ftype,
            "size": self.size,
            "sha256_hex": self.sha256_hex,
            "created_at": self.created_at,
            "note": self.note,
        }


class FirmwareStore:
    def __init__(self, root: Union[str, os.PathLike], signing_key: Optional[bytes] = None) -> None:
        self._root = os.path.abspath(root)
        self._key = signing_key
        os.makedirs(self._root, exist_ok=True)

    # -- 路径 ----------------------------------------------------------
    def _bin_path(self, version: int) -> str:
        return os.path.join(self._root, f"{version}.bin")

    def _meta_path(self, version: int) -> str:
        return os.path.join(self._root, f"{version}.meta.json")

    # -- 单调发布 ------------------------------------------------------
    def publish(self, package: FirmwarePackage, note: str = "") -> FirmwareMeta:
        """发布固件包，强制版本单调（R4）。"""
        ver = parse_version(package.version)
        existing = self.versions()
        if existing:
            max_ver = max(existing)
            if not is_newer(ver, max_ver):
                raise VersionMonotonicError(
                    f"仓库版本非单调：新 {ver} 须严格大于当前最大 {max_ver}"
                )
        # 写 blob
        with open(self._bin_path(ver), "wb") as f:
            f.write(package.blob)
        meta = FirmwareMeta(
            version=ver,
            ftype=package.ftype,
            size=len(package.payload),
            sha256_hex=package.sha256.hex(),
            created_at=time.time(),
            note=note,
        )
        with open(self._meta_path(ver), "w", encoding="utf-8") as f:
            json.dump(meta.as_dict(), f, ensure_ascii=False, indent=2)
        return meta

    # -- 查询 ----------------------------------------------------------
    def versions(self) -> List[int]:
        out: List[int] = []
        for fn in os.listdir(self._root):
            if fn.endswith(".bin"):
                try:
                    out.append(int(fn[:-4]))
                except ValueError:
                    continue
        return sorted(out)

    def latest(self) -> Optional[int]:
        vs = self.versions()
        return max(vs) if vs else None

    def has(self, version: Union[int, str]) -> bool:
        return parse_version(version) in self.versions()

    def meta(self, version: Union[int, str]) -> FirmwareMeta:
        ver = parse_version(version)
        p = self._meta_path(ver)
        if not os.path.exists(p):
            raise FileNotFoundError(f"无版本 {ver} 的元信息")
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        return FirmwareMeta(
            version=d["version"], ftype=d["ftype"], size=d["size"],
            sha256_hex=d["sha256_hex"], created_at=d["created_at"],
            note=d.get("note", ""),
        )

    def get_blob(self, version: Union[int, str]) -> bytes:
        ver = parse_version(version)
        p = self._bin_path(ver)
        if not os.path.exists(p):
            raise FileNotFoundError(f"无版本 {ver} 的封帧文件")
        with open(p, "rb") as f:
            return f.read()

    def get(self, version: Union[int, str]) -> FirmwarePackage:
        """取包并（若配置了密钥）校验签名完整性。"""
        blob = self.get_blob(version)
        if self._key is None:
            raise RuntimeError("FirmwareStore 未配置 signing_key，无法解包校验；请用 get_blob + 显式 unpack_package")
        return unpack_package(blob, self._key)
