# 系统总体架构

> 全新开发基线。思路沉淀自飞书 `NP@XLPS2`（历史验证思路，**仅参考、不复用代码**）。

## 1. 产品定义

XLPS2 托盘穿梭车（RGV）智能控制器，在密集仓储货架通道内自主行走、举升、搬运托盘。
对外承诺「开箱即用」：运抵现场无需改程序，环境差异（尤其环境光对光电干扰）靠**参数调整 + 设备自学习**消化。

- 业务场景：1000+ 条不连续独立轨道，RGV 随机放入执行取放货。
- 轨道分**有码**（条码/RFID，用于 WMS 仓位绑定）/ **无码**（仍定位与自学习，仅缺跨次持久化）。
- 定位基准 = **真0点**：靠近放入点的轨道物理端头；所有坐标 = `相对真0点距离(mm)`。
- 干扰点库以 `position_mm` 为索引（非轨道编号），无码轨道亦工作。

## 2. 四模块拓扑

```
            ┌────────────┐        MQTT/TLS         ┌────────────┐
 现场操作 ──▶│  HMI 安卓  │◀───────────────────────▶│  OTA 云端  │
            │ (React/TS) │   (telemetry/audit/log) │(Python+EMQX)│
            └─────┬──────┘                          └────────────┘
      RS485/CAN  │  (本地实时通道)
            ┌─────▼──────┐
            │  CFW 固件  │◀──CANopen CiA402──▶ 伺服 D_00(行走)/D_01(顶升)
            │ (STM32H7) │◀──RS485 Modbus────▶ 激光/传感器/网关
            └─────┬──────┘
            ┌─────▼──────┐
            │  EHW 硬件  │  24V隔离电源链 / 双CAN-FD / 双RS485 / RJ45 / 安全回路
            └────────────┘
```

## 3. 固件五层架构（CFW）

| 层 | 关注点 | 约束 |
|----|--------|------|
| L5 配置运维 | SMDL/参数/OTA/版本/日志 | 不直接碰硬件 |
| L4 应用行为 | 状态树/流转/轨道识别 | 经 L3 事件驱动 |
| L3 HSM 引擎 | 嵌套/正交/历史/事件分发/Guard（表驱动） | 纯通用，无 RGV 语义 |
| L2 服务层 | 事件总线/参数/自学习/滤波/诊断/位置校准 | 静态池，禁运行期 malloc |
| L1 HAL 抽象层 | IMotor/ILaser/IEncoder/IComm/IStorage | 实现底座 = ST HAL 库 |

层间只能经**接口/事件**调用下层，**严禁跨层访问寄存器**。运行期禁 `malloc`；ISR 最小化。

## 4. HSM 顶层状态（3 个并行正交区域）

```
System
├─ 区域1 主业务区：BOOTING→IDLE→TASK_RUNNING(组合)
│   ├─ FIND_ZERO(每次接任务找真0点)→TRACK_IDENTIFY(有码→IDENTIFIED/无码→ANONYMOUS)
│   ├─ DISPATCHING→TRAVELING(ACCEL→CRUISE→CHECK_DIST→DECEL→POSITIONING + NUDGE_RETRY + CROSS_VERIFY)
│   ├─ LOADING(伸叉→顶升→缩叉)/UNLOADING/RETURNING
├─ 区域2 能源管理区：POWER_NORMAL/LOW_BATTERY→CHARGING(带History)
└─ 区域3 安全监控区(最高优先级)：SAFE_OK/WARNING/ESTOP(全局捕获)
```

- 引擎纯通用；事件沿父链冒泡；历史状态支持充电抢占返回。
- `current_state` 编码见 ADR-003。

## 5. 接口

- 内部 CAN（CANopen CiA402）↔ 伺服 D_00(行走)/D_01(顶升)。
- RS485（Modbus RTU）↔ 激光/传感器/HMI 网关。
- HMI↔控制器：RS485 Modbus RTU 或 CANopen 网关（实时轮询+参数读写+任务下发，ADR-004）。
- 远程经 MQTT（10 主题，见契约）。

## 6. 事件订阅模型

发布-订阅事件总线（`evt_publish`/`evt_subscribe`，静态池无 malloc）。例：`EV_LOW_BATTERY`、`EV_OBSTACLE_DETECTED`。
模块互不感知，加功能不动老代码。

## 7. 跨模块契约

见 [`contract/`](contract/README.md)：33 字段数据字典、10 MQTT 主题、ADR-001~007。
SSOT 由主理人治理，变更须过 `tests/test_cross_module.py` 门禁（48/48）。
