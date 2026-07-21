# MQTT 主题（10 个，SSOT）

> 机器可读定义见 [`../config/mqtt_topics.json`](../config/mqtt_topics.json)。本文件为人类可读版本。

## 主题路径

```
rgv/{devId}/{topic}
```

`devId` 由路径承载，**不进入 payload**。以下 `{topic}` 为相对段。

## 主题表（8 基础 + ADR-002 扩展 2 = 10）

| # | 主题 | 方向 | QoS | 负载概要 |
|---|------|------|-----|----------|
| 1 | `ota/cmd` | cloud→device | 1 | OTA 指令（开始/暂停/确认/回滚），含 target_version、slot |
| 2 | `ota/data` | cloud→device | 1 | 固件/SMDL/参数分块：seq + CRC + chunk（断点续传） |
| 3 | `ota/progress` | device→cloud | 1 | ota_state / ota_progress_pct / ota_active_slot / ota_target_version |
| 4 | `ota/result` | device→cloud | 1 | ota_result = ok / fail / rollback |
| 5 | `param/set` | cloud→device | 1 | 参数热调（提交后 param_revision++，ADR-007） |
| 6 | `telemetry` | device→cloud | 1 | 统一遥测，33 字段（数据字典） |
| 7 | `config/smdl` | cloud→device | 1 | SMDL 下发：smdl_version / smdl_revision |
| 8 | `interference/sync` | device↔hmi/cloud | 1 | 干扰点库同步；Envelope = `{track_id, points:[{position_mm, confirmed, hit_count}]}` |
| 9 | `audit/log` | hmi→cloud | 1 | 操作审计（audit_seq 自增，ADR-002） |
| 10 | `diag/log` | device→cloud | 1 | 诊断/事件日志（diag_code，ADR-002） |

## interference/sync Envelope（权威）

```json
{
  "track_id": 123,
  "points": [
    { "position_mm": 4500, "confirmed": true, "hit_count": 7 }
  ]
}
```

## 门禁

`tests/test_cross_module.py` 校验：主题数=10、必填键（topic/direction/qos/payload）齐全、`devId` 不出现在 payload。
