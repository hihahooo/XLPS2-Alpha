# 文档⑦ 接口定义（Interface Definitions）

> 八文档之一。连接器引脚定义；与 `sch/03_interfaces.md`、`pinmap.csv` 一致；协议遵循 SSOT 契约。

## 1. J1 — 24V 输入（5.08 端子）

| 脚 | 信号 | 说明 |
|----|------|------|
| 1 | +24V_IN | 标 + |
| 2 | GND_IN | 标 − |

## 2. J2 / J3 — 隔离 CAN-FD（M12-4，D_00/D_01）

| 脚 | 信号 | 说明 |
|----|------|------|
| 1 | CANH | 终端 120Ω |
| 2 | CANL | 终端 120Ω |
| 3 | GND_ISO | 总线侧隔离地 |
| 4 | Shield/NC | 屏蔽（接机壳） |

- 协议：CANopen CiA402（由 CFW 实现）；硬件透明。

## 3. J4 / J5 — 隔离 RS485（M12-4，激光/网关）

| 脚 | 信号 | 说明 |
|----|------|------|
| 1 | A | 上拉 680Ω |
| 2 | B | 下拉 680Ω |
| 3 | GND_ISO | 总线侧隔离地 |
| 4 | Shield/NC | 屏蔽 |

- 协议：Modbus RTU；任务下发 FC=0x10，保持寄存器基址 0x2000（**ADR-004**）。
- 与 CANopen 伺服控制解耦（Modbus 仅下发任务语义）。

## 4. J14 — RJ45 以太网（HR911105A，带磁芯）

- 标准 RJ45 8 针；内部磁芯提供 1500V 网络隔离。
- 用途：本地调试 / OTA 网关侧（MQTT 经 WS63 或本口上行）。
- **裁定标注（#4）：保留 ETH 功能，列为「空间紧张时可裁剪项」**；若 100×80mm 布局拥挤可裁剪，由 WS63 无线/调试口替代功能。

## 5. J6 — SWD 调试（1.27mm 5P）

| 脚 | 信号 |
|----|------|
| 1 | VCC(3.3) |
| 2 | SWDIO |
| 3 | SWCLK |
| 4 | NRST |
| 5 | GND |

## 6. J13 — 扩展排针（2×10 2.54）

- 含：NET_3V3、GND、NET_5V、NET_24V_BOARD、保留 GPIO/ADC/SPI/I2C、调试串口(USART1 PA9/PA10)。

## 7. 无线 WS63（板载模组，非连接器）

- SDIO（SDMMC1）高速数传 + UART4(PA0/PI9) AT 指令。
- 协议：MQTT（10 主题，见 `config/mqtt_topics.json`）；WiFi/星闪/BLE 物理层。
- **裁定标注（#5）：保留 SDIO+UART4 方案**；引脚 AF 须由 M2（CFW）在 CubeMX 终校后落地。

## 8. 审查清单

- [ ] 连接器料号统一（J14=HR911105A）
- [ ] 引脚定义与 pinmap.csv 一致
- [ ] Modbus 基址 0x2000 / FC=0x10 与 ADR-004 一致
- [ ] 隔离地(GND_ISO)与逻辑地(NET_GND)分割正确
