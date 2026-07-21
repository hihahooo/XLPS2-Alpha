# XLPS2-Alpha 控制器 — 原理图源（Schematic Source）

> 全新开发基线。EDA 环境（KiCad）未安装，本目录以**等价可交付设计源**形式给出：
> 分层原理图叙述（本目录 01~04）+ 网表 `netlist.csv` + 器件/符号索引 `symbols.csv`。
> 投板前由 KiCad/LCEDA 按本源重绘 `.sch` 并导出正式网表，须与本文件逐项核对。

## 设计总纲

| 项 | 规格 |
|----|------|
| MCU | STM32H743IIT6（LQFP176，2MB 内部 Flash，1MB SRAM） |
| 板型 | 2 层 PCB，100×80mm，1.6mm，ENIG；禁用 4 层，无内层平面 |
| 输入 | DC 24V（动力 48V 由机柜另供，不经本板） |
| 隔离 | 系统级：U30 隔离 DC-DC（≥1.5kV）；总线级：CAN/RS485 隔离收发器 |
| 工作温度 | −30~+60℃（系统）；器件级更宽 |
| 丝印/装配 | 见 `../docs/04_silkscreen.md`、`../docs/05_assembly.md` |

## 原理图分册（本目录）

| 文件 | 内容 |
|------|------|
| `01_power_chain.md` | 24V 隔离电源链逐级设计与验证（J1→L30→Q10→F1→U31→U30→NET_24V_BOARD） |
| `02_mcu_min_system.md` | STM32H743 最小系统（电源域/晶振/复位/Boot/SWD/Flash A-B） |
| `03_interfaces.md` | 接口（隔离 CAN-FD×2 / 隔离 RS485×2 / RJ45-ETH / WS63 / SWD） |
| `04_safety.md` | 安全回路（ESTOP/安全触边硬件直切 + IWDG 心跳使能） |
| `netlist.csv` | 信号网表（Net → 器件:引脚），可追溯到每一册 |
| `symbols.csv` | 器件/符号索引（位号、型号、封装、参数），与 `../bom/bom.csv` 对应 |

## 网表追溯原则

- 8 份交付文档（`../docs/01~08`）中的位号、封装、参数必须与 `symbols.csv` / `bom/bom.csv` 完全一致。
- 任何「绕过 24V 保护链」的改法视为 QA 不通过（链序：防反 → 保险 → eFuse → 隔离，绝对不可颠倒）。
- 地分割：`NET_GND_IN`（初级，U30 前）与 `NET_GND`（次级，U30 后）≥4mm creepage。
