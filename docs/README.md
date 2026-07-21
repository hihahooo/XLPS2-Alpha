# XLPS2-Alpha 文档索引

本目录为 XLPS2 托盘穿梭车控制器项目的架构与开发说明。所有内容面向**全新开发**，不复用历史验证代码。

## 阅读顺序

1. [系统总体架构](overview.md) — 四模块拓扑、数据流、分层
2. 逐模块架构与开发说明
   - [CFW 控制器固件](modules/cfw.md)
   - [EHW 嵌入式硬件](modules/ehw.md)
   - [HMI 安卓应用](modules/hmi.md)
   - [OTA 云端升级](modules/ota.md)
3. [跨模块契约（SSOT）](contract/README.md) — 数据字典、MQTT 主题、ADR
4. [SSOT 治理与验收](governance.md) — ADR 列表、门禁、里程碑 WP3–WP12
5. [开发工作流](dev-guide.md) — SOP、调度、双人复核

## 设计来源

- 思路沉淀自飞书知识库 `NP@XLPS2`（历史验证，**仅参考不复用**）。
- 目录框架遵循本仓库既有结构（`src/ docs/ tests/ scripts/ config/`）。

## 契约 artifacts（SSOT）

位于仓库根 `config/`：

- `config/data_dictionary.json` — 33 字段
- `config/mqtt_topics.json` — 10 主题
- ADR 文档见 [`contract/`](contract/README.md)
