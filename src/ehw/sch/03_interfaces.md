# 接口设计（CAN-FD / RS485 / RJ45-ETH / WS63 / SWD）

> 所有现场总线均位于**隔离次级域（NET_GND）**；CAN/RS485 另加**总线级隔离收发器**，RJ45 由磁芯隔离。

## 1. 隔离 CAN-FD ×2（内部伺服 D_00 行走 / D_01 顶升）

| 路 | 收发器 | MCU 侧 | 总线侧 | 连接器 |
|----|--------|--------|--------|--------|
| CAN1（D_00） | U2A=ISO1042（隔离 CAN-FD） | FDCAN1: PA11(RX)/PA12(TX) | CANH/CANL + 120Ω 终端 | J2（M12-4 或 4-pin 端子） |
| CAN2（D_01） | U2B=ISO1042 | FDCAN2: PB12(RX)/PB13(TX) | CANH/CANL + 120Ω 终端 | J3 |

- 隔离电源：每路总线侧由独立 B0505S（U40/U41，5V→5V 隔离 1W）供给 ISO1042 的 VCC2。
- 防护：总线端并联 SM712 TVS（D_CAN1/D_CAN2）到隔离地，钳位 ±15kV ESD / 浪涌。
- 终端：120Ω 置于 J2/J3 端（默认焊接，可由 0Ω 选择）；终端电阻接隔离地。
- 协议：CANopen CiA402（由 CFW 实现，硬件仅透明传输）。

## 2. 隔离 RS485 ×2（Modbus RTU：激光/传感器 / HMI 网关）

| 路 | 收发器 | MCU 侧 | 总线侧 | 连接器 |
|----|--------|--------|--------|--------|
| RS485-1（激光/传感器） | U3A=ADM2483（隔离 RS485） | USART3: PB10(TX)/PB11(RX)，DE=PB14 | A/B + 120Ω 终端 | J4 |
| RS485-2（HMI 网关） | U3B=ADM2483 | USART6: PC6(TX)/PC7(RX)，DE=PG8 | A/B + 120Ω 终端 | J5 |

- 隔离电源：每路总线侧由 B0505S（U42/U43）供给 ADM2483 的 VCC2。
- 防护：总线端 SM712 TVS（D_RS1/D_RS2）+ 自恢复保险（可选）。
- 偏置：总线 A 上拉(680Ω)、B 下拉(680Ω) 至隔离侧电源，确保空闲态确定。
- 协议：Modbus RTU，任务下发 FC=0x10 基址 0x2000（ADR-004）；与 CANopen 伺服控制解耦。

## 3. RJ45 以太网（ETH，LAN8742A + HR911105A）

| 信号 | MCU 引脚 | PHY | 说明 |
|------|----------|-----|------|
| ETH_MDC | PC1 | LAN8742A MDC | MDIO 时钟 |
| ETH_MDIO | PA2 | MDIO | 管理数据 |
| RMII_REF_CLK | PA1 | REF_CLK(50MHz 由 PHY 输出) | 来自 PHY 的 50MHz 参考 |
| RMII_CRS_DV | PA7 | CRS_DV | |
| RMII_RXD0/1 | PC4/PC5 | RXD0/1 | |
| RMII_TX_EN | PG11 | TX_EN | |
| RMII_TXD0/1 | PG13/PG12 | TXD0/1 | |
| PHY_RST | PC0 | nRST | MCU 控制复位 |
| PHY_INT | PI2 | nINT | 中断/链接状态 → MCU |

- 连接器 J14 = **HR911105A**（HanRun 带集成磁芯 RJ45），提供 1500V 网络隔离。
- 50MHz 时钟由 LAN8742A 晶振产生并回灌 MCU（RMII 从模式）。
- 用途：本地调试 / OTA 网关侧（固件经 MQTT 由 WS63 或本口上行）。
- **裁定标注（#4）：保留 ETH，列为「空间紧张时可裁剪项」**（布局拥挤可由 WS63/调试口替代）。
- 防护：HR911105A 磁芯即隔离；差分对并 SM712 TVS（D_ETH，网口侧）抑 ESD。

> **主理人 #4 标注（保留，可裁剪）**：LAN8742A + HR911105A 裁定保留；若 100×80mm 布局拥挤，
> 标注为「**空间紧张时可裁剪项**」——裁剪后调试/OTA 上行由 WS63 无线或 SWD 调试口替代。

## 4. 无线模组 WS63（WiFi / 星闪 / BLE）

| 接口 | MCU 引脚 | 说明 |
|------|----------|------|
| SDIO（固件/数据） | SDMMC1: PC12(CK)/PD2(CMD)/PC8(D0)/PC9(D1)/PC10(D2)/PC11(D3) | 高速数传主通道 |
| AT 串口 | UART4: PA0(TX)/PI9(RX) | AT 指令/低速控制 |
| 状态 | PG6(READY)/PG7(nRST) | 模组就绪/复位 |

- 模组由 NET_3V3 经磁珠单独供电，地接 NET_GND；天线经板边 μ.FL 或板载 PCB 天线。
- 用途：MQTT 上云（telemetry/ota/param… 见 `config/mqtt_topics.json`）。
- **裁定标注（#5）：保留 SDIO+UART4 方案**；引脚 AF 须由 M2（CFW）在 CubeMX 终校后落地。

> **主理人 #5 标注（实现冻结，待 M2 终校）**：暂以 SDIO(SDMMC1)+UART4(AT) 实现；
> 接口引脚初值见 `pinmap.csv`，**M2 里程碑经 CubeMX 对照 WS63 规格书终校**（SDIO 速率/AT 波特率/复位时序）。

## 5. 外部存储（干扰点库 / 标定）

| 器件 | 接口 | 引脚 | 用途 |
|------|------|------|------|
| U6 FM24CL64（FRAM 64Kb） | I2C1 | PB6(SCL)/PB7(SDA) | 干扰点库（position_mm 索引，掉电不丢） |
| U7 24C64（EEPROM） | I2C1 | PB6/PB7（同总线，地址区分） | 序列号/标定/密钥 |

- 上拉：SCL/SDA 各 4.7kΩ 至 NET_3V3；总线速率 ≤400kHz。

## 6. 调试/扩展

- J6：SWD 1.27mm 5pin（详见 `02_mcu_min_system.md` §5）。
- J13：2×10 2.54mm 排针（扩展：空闲 GPIO/ADC/SPI/I2C/电源测试），含 NET_3V3/GND/5V/24V 测试抽头。
- 调试串口：USART1（PA9/PA10）预留作控制台（与上不冲突）。
