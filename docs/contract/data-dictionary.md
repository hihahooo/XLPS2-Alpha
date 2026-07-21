# 数据字典（33 字段，SSOT）

> 机器可读定义见 [`../config/data_dictionary.json`](../config/data_dictionary.json)。本文件为人类可读版本。

## 来源

LTM v3：基础 18 字段 + ADR-001 扩展 15 字段 = **33 字段**。

## 规范

- `task_status` 为唯一命名，**禁止** `task_state` 别名。
- OTA 传输专有字段（seq / CRC / 验签状态 / pending / active_slot / health_deadline / 健康回执）**不进入**本字典（见 ADR-006），仅作 MQTT 载荷内部字段或存 FLAG 扇区。
- 干扰点库以 `position_mm` 为索引（非轨道编号），无码轨道亦可工作。

## 字段表

| # | 字段 | 类型 | 单位 | 来源 | 上报主题 | 说明 |
|---|------|------|------|------|----------|------|
| 1 | current_state | uint16 | — | CFW | telemetry | ADR-003 层级编码；0xFFFF=未初始化 |
| 2 | position_mm | int32 | mm | CFW | telemetry | 相对真0点距离 |
| 3 | speed_mm_s | int16 | mm/s | CFW | telemetry | 当前速度 |
| 4 | battery_soc | uint8 | % | CFW | telemetry | 电池 SOC 0-100 |
| 5 | track_id | uint32 | — | CFW | telemetry | 0=无码匿名 |
| 6 | task_status | enum | — | CFW | telemetry | 任务状态（禁 task_state） |
| 7 | task_progress_pct | uint8 | % | CFW | telemetry | 进度 0-100 |
| 8 | fault_code | uint16 | — | CFW | telemetry | 故障码 |
| 9 | fault_level | uint8 | — | CFW | telemetry | 故障级别 1-4（ADR-006） |
| 10 | motor_current_a | float | A | CFW | telemetry | 电机电流 |
| 11 | motor_temp_c | int8 | °C | CFW | telemetry | 电机温度 |
| 12 | encoder_position | int32 | cnt | CFW | telemetry | 编码器位置 |
| 13 | laser_status | enum | — | CFW | telemetry | 激光状态 |
| 14 | photoelectric_state | enum | — | CFW | telemetry | 光电开关量 |
| 15 | ota_active_slot | enum | — | OTA | ota/progress | 激活分区 A/B |
| 16 | ota_state | enum | — | OTA | ota/progress | OTA 状态机 |
| 17 | ota_progress_pct | uint8 | % | OTA | ota/progress | OTA 进度 |
| 18 | ota_target_version | string | — | OTA | ota/progress | 目标版本（单调） |
| 19 | ota_result | enum | — | OTA | ota/result | ok/fail/rollback |
| 20 | fw_version | string | — | CFW | telemetry | 固件版本 |
| 21 | smdl_version | string | — | CFW | config/smdl | SMDL 版本 |
| 22 | param_revision | uint32 | — | CFW | config/smdl | 参数修订（热调自增） |
| 23 | smdl_revision | uint32 | — | CFW | config/smdl | SMDL 修订 |
| 24 | interference_count | uint16 | — | CFW | interference/sync | 干扰点计数 |
| 25 | diag_code | uint16 | — | CFW | diag/log | 诊断码 |
| 26 | audit_seq | uint32 | — | HMI | audit/log | 审计序号 |
| 27 | top_state | enum | — | CFW | telemetry | 顶层状态 |
| 28 | sub_state | enum | — | CFW | telemetry | 子状态 |
| 29 | region | uint8 | — | CFW | telemetry | 正交区域 0/1/2 |
| 30 | is_safe | bool | — | CFW | telemetry | 安全回路状态 |
| 31 | command_in | enum | — | HMI | telemetry | 入站指令 |
| 32 | heartbeat_ts | uint32 | s | CFW | telemetry | 心跳时间戳 |
| 33 | uptime_s | uint32 | s | CFW | telemetry | 上电时长 |

## 门禁

`tests/test_cross_module.py` 校验：字段数=33、字段名唯一、必填键齐全、类型/范围符合。
