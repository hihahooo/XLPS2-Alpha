# STM32H743IIT6 最小系统

> MCU：STM32H743IIT6（LQFP176，Cortex-M7 400MHz，2MB 内部 Flash，1MB SRAM，内置 ETH MAC）

## 1. 电源域

| 域 | 引脚 | 电压 | 处理 |
|----|------|------|------|
| 核心 1.8V（内部 LDO） | VCAP_1(PI6? 实际 VCAP_1/VCAP_2) | 1.8V | 各接 2.2µF 到 VSS（**不可省**，决定内核稳定） |
| 主数字 VDD | VDD×多引脚（见封装） | 3.3V | 每对 VDD/VSS 旁 100nF；大电流区加 10µF |
| 模拟 VDDA | VDDA(20) | 3.3V | 经磁珠从 NET_3V3 取，旁 1µF+100nF；VREF+ 接 3.3V 经 100nF |
| 备份域 VBAT | VBAT | 3.0V | 经肖特基由 NET_3V3 与 CR1220(BT1) 双电源切换，供 RTC/备份寄存器 |
| PHY 5V | — | 5V | 由 NET_5V 经磁珠供给 LAN8742A |

**退耦原则**：2 层板无完整参考平面，VDD 采用「星型+网格」走线，每个 VDD 引脚 <5mm 内 100nF；
所有 VCAP 必须紧靠芯片；模拟/数字地在单点（芯片下方）经 0Ω/磁珠连接。

## 2. 晶振

| 晶振 | 引脚 | 参数 | 负载 |
|------|------|------|------|
| HSE Y1 | PH0(OSC_IN)/PH1(OSC_OUT) | 25MHz，±10ppm，18pF | 2×22pF（C_Y1a/C_Y1b），走线 ≤10mm 对称包地 |
| LSE Y2 | PC14(OSC32_IN)/PC15(OSC32_OUT) | 32.768kHz，±20ppm | 2×12pF，远离数字噪声 |

> HSE 25MHz 经 PLL 得 400MHz SYSCLK；LSE 供 RTC（断电由 BT1 维持）。

## 3. 复位

| 信号 | 引脚 | 处理 |
|------|------|------|
| NRST | Pin15 | 10k 上拉至 NET_3V3 + 100nF 到 GND；外接 U8(IMP811T，3.08V 监控) 推挽复位 |
| 手动复位 | SW1 | 接 NRST 经 1k 到 GND（按键低有效） |

## 4. Boot 配置

| 信号 | 引脚 | 接法 |
|------|------|------|
| BOOT0 | PH3 | 10k 下拉（默认从 Flash 启动）；经 0Ω 可选上拉进 DFU/系统 Boot |
| BOOT1(nBOOT1 为选项字节，无专用脚) | — | 由 Option Bytes 决定，硬件仅留 BOOT0 |

> 出厂默认 BOOT0=0 → 从内部 Flash 启动（A/B 由 OTA 标志切换，见 ADR-005）。

## 5. 调试接口 SWD/JTAG

| 信号 | 引脚 | 连接器 |
|------|------|--------|
| SWCLK/TCK | PA14 | J6（1.27mm 5pin SWD：VCC/SWDIO/SWCLK/NRST/GND） |
| SWDIO/TMS | PA13 | J6 |
| NRST | Pin15 | J6 |
| 保留 JTAG | PB3/PB4（JTDO/NJTRST） | 复用，默认 SWD 即可 |

## 6. Flash 分区（A/B 双分区，SSOT=ADR-005）

| 区域 | 基址 | 容量 | 说明 |
|------|------|------|------|
| Boot/Option | 0x08000000–0x0801FFFF | 128KB | Bootloader + 选项字节 + 出厂参数区 |
| A 分区 | 0x08020000 | ≤0x0E0000（~0.875MB） | 激活/备用固件（A/B 物理同芯片） |
| B 分区 | 0x08100000 | ≤0x0E0000（~0.875MB） | 对端固件 |
| FLAG 扇区 | 0x081E0000 | 双备份(0x000/0x200)+CRC32 | 当前槽/健康状态（ADR-005） |

- 内部 Flash 2MB（0x08000000–0x081FFFFF）容纳 A/B+FLAG，余量用于 SMDL/参数区。
- **不依赖外部 QSPI 启动**；外部 FRAM/EEPROM 仅存干扰点库/标定（见 `03_interfaces.md`）。
- ✅ **主理人 #1 已裁决**：ADR-005 文字已更正为「STM32H743IIT6 内部 Flash 2MB（单芯片内 A/B 逻辑双分区）」，
  删除原「GD25Q127 ×2」外部 Flash 表述。本设计即按内部 Flash 实现 A/B，与更正后 ADR-005 完全一致，**无需改动**。

## 7. 看门狗与系统安全

- IWDG（独立看门狗）：由 LSI 驱动，固件定期喂狗；超时（~1s）触发硬件复位。
- 安全使能心跳：MCU 经 GPIO 持续翻转「安全使能」信号，驱动伺服使能链（见 `04_safety.md`）；
  固件挂死 → IWDG 复位或心跳停 → 安全继电器释放 → 动力切除（与 HSM region=2 对应）。
