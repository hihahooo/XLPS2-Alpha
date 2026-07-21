# CFW — 控制器固件（STM32H7）

> 全新脚手架。**不复用**任何历史验证代码；仅沿用 NP@XLPS2 知识库中沉淀的可落地架构思路。

## 职责

托盘穿梭车控制器核心固件：运动控制、传感器采集（RS485 激光测距）、与上层通信（CANopen / MQTT 网关）、本地状态机（HSM）、OTA 本地端执行。

## 技术栈

- MCU：STM32H743（Cortex-M7，带 HSM 外设）
- 构建：STM32CubeMX + CMake + arm-none-eabi-gcc
- 通信：CANopen（参考步科 FD135 对象字典）、RS485（激光传感器）、RJ45（OTA/MQTT 网关侧）

## 五层架构（目标）

| 层 | 关注点 |
|----|--------|
| L1 HAL/驱动 | GPIO/CAN/USART/ETH 底层驱动 |
| L2 外设抽象 | 电机、编码器、激光、CANopenNode 封装 |
| L3 控制算法 | 运动规划、定位、避障 |
| L4 HSM 状态机 | 分层状态机（ADR 待补：顶层状态 + 转移） |
| L5 应用/契约 | 事件订阅、MQTT 网关桥接、OTA 本地端 |

## 目录（建议）

```
src/cfw/
  core/        # 启动、调度、看门狗
  hal/         # L1 驱动
  driver/      # L2 外设抽象
  control/     # L3 控制算法
  hsm/         # L4 状态机
  app/         # L5 应用与契约桥接
  ota/         # OTA 本地端（A/B 分区）
```

## 开发说明

- P0-1 / P0-2 止血项优先（详见架构总文档）。
- 事件订阅模型：模块内发布/订阅，降低耦合。
- 所有对外字段遵循 `config/data_dictionary.json`（SSOT）。
