# XLPS2-Alpha

> XLPS2 托盘穿梭车控制器 —— 软硬件产品架构方案与开发说明（全新开发基线）。

本仓库是 XLPS2 托盘穿梭车控制器项目的**全新开发基线**。架构思路沉淀自飞书知识库
`NP@XLPS2`（历史验证思路，**仅参考、不复用其代码**），目录框架遵循本仓库既有结构。

## 产品定义

托盘穿梭车（Pallet Shuttle / RGV）控制器：在密集仓储货架通道内自主行走、举升、搬运托盘。
控制器负责运动控制、定位、通信与远程升级，现场通过安卓 HMI 交互，云端通过 OTA 统一升级。

## 四模块架构

| 模块 | 代码 | 职责 | 技术栈 |
|------|------|------|--------|
| 控制器固件 | CFW | 运动/定位/状态机/本地 OTA | STM32H7，五层架构，HSM，CANopen，RS485 |
| 嵌入式硬件 | EHW | 电源/接口/无线承载 | 2 层 PCB，24V 隔离电源链，STM32H743 |
| 安卓 HMI | HMI | 现场交互/监控/配置 | React+Vite+TS+Zustand，Capacitor apk，JWT RBAC |
| 云端 OTA | OTA | 远程升级/回滚 | Python + EMQX MQTT，A/B 双分区 |

## 目录结构

```
XLPS2-Alpha/
├── src/
│   ├── cfw/   # 控制器固件（STM32H7）
│   ├── ehw/   # 硬件设计（原理图/PCB/BOM）
│   ├── hmi/   # 安卓 HMI 应用
│   └── ota/   # 云端 OTA 服务
├── docs/      # 架构与开发文档（见 docs/README.md）
├── config/    # SSOT 契约 artifacts（数据字典 / MQTT 主题 / 构建配置）
├── tests/     # 跨模块契约门禁（test_cross_module.py，48/48）
├── scripts/   # 构建 / 运维脚本
└── .github/   # CI
```

## SSOT 契约（单一事实源）

跨模块一致性由仓库内 `config/` 统一维护，主理人（Tech Lead）治理：

- 数据字典：33 字段（`config/data_dictionary.json`）
- MQTT 主题：10 个（`config/mqtt_topics.json`）
- `current_state` 编码：ADR-003
- OTA A/B 双分区：ADR-005
- 四级容错：ADR-006

## 开发约定

- 主分支 `main`；功能在独立分支开发，PR 合入。
- 提交语义化（`feat:` / `fix:` / `chore:`）。
- 跨模块变更必须过 `tests/test_cross_module.py` 门禁（48/48）。

## 快速开始

```bash
git clone git@github.com:hihahooo/XLPS2-Alpha.git
cd XLPS2-Alpha
bash scripts/build.sh gate      # 跑跨模块契约门禁
```

> 详细架构与逐模块开发说明见 [`docs/`](docs/README.md)。
