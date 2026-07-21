# SSOT 治理与验收

> 跨模块一致性由本目录统一治理。主理人（Tech Lead）为唯一维护者。

## 1. 单一事实源（SSOT）

| 工件 | 位置 | 内容 |
|------|------|------|
| 数据字典 | `config/data_dictionary.json` | 33 字段 |
| MQTT 主题 | `config/mqtt_topics.json` | 10 主题 |
| ADR | `docs/contract/adr-*.md` | ADR-001~007 |

任何模块改动若触及上述契约，必须同步更新此处并过 `tests/test_cross_module.py` 门禁。

## 2. ADR 全清单

| ADR | 主题 | 要点 |
|-----|------|------|
| ADR-001 | 扩展字段 +15 | 统一字典 = 基础18 + 15 = 33 |
| ADR-002 | 扩展主题 +2 | 10 主题（audit/log、diag/log） |
| ADR-003 | current_state 层级编码 | (region<<14)\|(top_state<<8)\|sub_state；0xFFFF=未初始化 |
| ADR-004 | 任务下发 Modbus | FC=0x10，基址 0x2000 |
| ADR-005 | OTA A/B 双分区 | A=0x08020000 / B=0x08100000 / FLAG=0x081E0000；HEALTH_WINDOW_S=300；CHUNK_SIZE=1024；mqtts://emqx.np-xltech.com:8883 |
| ADR-006 | 四级容错 | CHECK_DIST→NUDGE_RETRY→CROSS_VERIFY→SLOW_STOP/ESTOP；OTA 专有字段不进字典 |
| ADR-007 | 恢复出厂 / 参数版本 | factory_reset_req 复位参数层 + param_version++；热调 param_version++ |

## 3. 验收门禁

- **跨模块契约门禁**：`tests/test_cross_module.py`（目标 48/48）。
- **P0 / P1 双人复核**：关键修复与规则变更须两人确认。
- **WP12 端到端验收**：联调通过后签字，更新飞书 `NP@XLPS2` LTM v3（SSOT 镜像）。

## 4. 里程碑（WP3–WP12）

按标准 SOP 映射为工作包：

| 阶段 | 工作包 | 内容 |
|------|--------|------|
| 需求拆解 | WP3 | 任务按模块拆分，明确契约边界 |
| 模块并行执行 | WP4–WP7 | CFW / EHW / HMI / OTA 各自实现（P0-1/P0-2 止血优先） |
| 跨模块契约对齐 | WP8 | 33 字段 / 10 主题 / ADR-003/005/006 三方逐字一致校验 + 门禁 |
| 评审与联调 | WP9–WP11 | P0/P1 双人复核，端到端联调 |
| 验收 | WP12 | 端到端门禁与签字，更新 LTM v3 |

> 注：WP 编号沿用历史验证阶段的阶段划分；XLPS2-Alpha 实际排期以主理人发布为准。

## 5. do-NOT-reuse 警示

- **禁止复用** `NP@XLPS2` 历史验证代码（固件/硬件/HMI/OTA 任何实现）。
- 仅可参考其沉淀的**可落地思路**（架构、契约、ADR）。
- 全新基线从本仓库脚手架起步。

## 6. 歧义项（以本 SSOT 为准）

历史文档存在需主理人裁定的歧义，XLPS2-Alpha 一律以本仓库 `config/` + `docs/contract/` 为准：

1. Flash 容量：LTM 写 1MB，doc2/3/7 写 2MB → 以 STM32H743IIT6 实际 2MB 为准，A/B 各 ≤0x0E0000。
2. 33 字段与 doc2/3 §6.3 示例子集（18~19 个）范围差异 → 以 LTM v3 的 33 字段权威列表为准。
3. OTA 私有 5 字段隔离表述 → 以 ADR-006（传输专有字段不进字典）+ 数据字典 33 字段列表共同约束。

## 7. 推送策略与知识管理约定（2026-07-21 项目启动指令）

依据项目启动指令，对原 SOP 作如下约束调整（**不影响正常开发流程**）：

### 7.1 代码推送策略
- **GitHub 推送暂停**：暂不向 GitHub `hihahooo/XLPS2-Alpha` 推送代码。
- **保留推送接口**：`scripts/build.sh`、CI（`.github/workflows/ci.yml`）、跨模块门禁 `tests/test_cross_module.py`，以及 GitHub MCP 推送路径（`create_or_update_file` 逐文件）**全部保留，不因暂停推送而移除**。
- **统一推送**：待公司授权（连接器获 `contents: write`）后，由主理人统一执行推送——保留骨架 `.codebuddy/`、`.mcp.json`、`CODEBUDDY.md`、`.gitignore`，覆盖 `README.md` 为交付版，新增 `docs/config/tests/scripts/src`。
- 该策略不影响四模块正常开发与本地/飞书文档归档。

### 7.2 知识管理（长期记忆 + 文档归档）
- **阶段性长期记忆**：按开发阶段（启动 / 模块实现 / 跨模块对齐 / 联调验收）生成长期记忆，**双写**至本地存储（工作区 `memory/` + 本地归档）与飞书知识库 `XLPS2-Alpha`。
- **文档统一归档**：开发过程中产生的所有项目文档（架构、契约、ADR、模块实现说明、评审/会议记录等）**统一推送至飞书知识库 `XLPS2-Alpha`**，不得分散存储。
- **开发依据**：飞书 `XLPS2-Alpha` 现有 18 节点文档已确认，作为各模块全量开发的依据。
