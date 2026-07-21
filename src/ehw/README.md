# XLPS2-Alpha 嵌入式硬件（EHW）设计产物

> 全新开发基线（**不复用** NP@XLPS2 历史设计，仅参考思路）。EDA(KiCad) 未安装，
> 以等价可交付设计源形式交付：分层原理图叙述 + 网表 + 符号/封装库 + 8 文档自洽集 + BOM + 引脚表。
> 投板前由 KiCad/LCEDA 按本目录重绘 `.sch/.kicad_pcb`，须与下列源逐项核对。

## 目录与产物

| 路径 | 内容 | 对应交付 |
|------|------|----------|
| `sch/README.md` | 原理图源总纲 | — |
| `sch/01_power_chain.md` | 24V 隔离电源链逐级设计+验证 | 电源链 |
| `sch/02_mcu_min_system.md` | STM32H743 最小系统 | MCU |
| `sch/03_interfaces.md` | CAN-FD/RS485/RJ45/WS63/I2C | 接口 |
| `sch/04_safety.md` | ESTOP/触边硬件直切 + IWDG 心跳 | 安全 |
| `sch/netlist.csv` | 信号网表（Net→器件:引脚） | 可追溯 |
| `sch/symbols.csv` | 器件/符号索引 | 与 BOM 对应 |
| `pcb/stackup.md` | 2 层板层叠与约束 | 布局 |
| `pcb/layout.md` | 分区布局与布线规则 | 布局 |
| `bom/bom.csv` | BOM（35 项，合计 ¥504.62） | 成本 |
| `pinmap.csv` | STM32H743 引脚分配表 | 引脚 |
| `lib/footprints.md` | 封装库索引 | 库 |
| `docs/01_schematic.md` | 文档① 原理图 | 8 文档 |
| `docs/02_layout.md` | 文档② 布局 | 8 文档 |
| `docs/03_bom.md` | 文档③ BOM | 8 文档 |
| `docs/04_silkscreen.md` | 文档④ 丝印 | 8 文档 |
| `docs/05_assembly.md` | 文档⑤ 装配 | 8 文档 |
| `docs/06_testpoints.md` | 文档⑥ 测试点 + HW-PWR-001~005 | 8 文档 |
| `docs/07_interfaces.md` | 文档⑦ 接口定义 | 8 文档 |
| `docs/08_power.md` | 文档⑧ 功耗预算 | 8 文档 |
| `docs/selfcheck.md` | 8 维交叉自洽校验 | 一致性 |

## 八文档自洽结论

设计态 8/8 PASS（见 `docs/selfcheck.md`）。样机实测（HW-PWR-001~005、ICT）为投板后验收，不阻塞文档自洽。

## 关键设计常量（SSOT 对齐）

- 24V 链序：J1→L30→Q10→F1→U31→U30→NET_24V_BOARD（**不可颠倒**）。
- Flash 分区（ADR-005，内部 2MB）：A=0x08020000 / B=0x08100000 / FLAG=0x081E0000，各 ≤0x0E0000。
- eFuse 限流：R_ILIM=6.04kΩ → I_LIM≈1.95A（依 TI 公式 11.8/R_ILIM 核算；主理人 #2 裁决确认 ≈2A）。
- 隔离：系统级 U30(≥1.5kV) + 总线级 ISO1042/ADM2483 + B0505S（主理人 #3 保留，~¥88.8 降本候选）；RJ45 磁芯隔离。
- 连接器料号统一：J14=HR911105A（非 HR601680）。
- 板型：2 层 100×80mm，禁用 4 层。

## 主理人裁定采纳（#1~#5 已裁决，无遗留）

主理人裁决已全部采纳（设计态 8/8 通过）：#1 ADR-005 已更正为内部 Flash 2MB 逻辑双分区（本设计无需改动）；#2 R_ILIM=6.04kΩ≈1.95A；#3 保留双隔离边界（降本候选）；#4 保留 RJ45（可裁剪）；#5 WS63 维持 SDIO+UART4（M2 CubeMX 终校）。详见 `docs/selfcheck.md` 与 `docs/modules/ehw.md` §10。
