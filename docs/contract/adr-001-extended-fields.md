# ADR-001 扩展字段（+15）

- 状态：采纳（SSOT）
- 背景：基础 18 字段不足以支撑自学习、OTA、四级容错与任务下发的可观测性。
- 决策：在统一字典中扩展以下 15 字段：

```
cross_verify_fault_ch      # 交叉验证故障通道
nudge_retry_index          # 微动重试序号
ota_active_slot            # 当前激活分区
smdl_validate_result       # SMDL 校验结果
estop_reason               # 急停原因
interference_confirmed     # 干扰点已确认
interference_hit_count     # 干扰点命中次数
param_version              # 参数版本
task_id                    # 任务ID
task_status                # 任务状态（禁 task_state 别名）
task_target_pos_mm         # 任务目标位置
task_axis                  # 任务轴（1=D_00行走 / 2=D_01顶升）
find_zero_speed            # 找零速度
preview_mm                 # 预览距离
factory_reset_req          # 恢复出厂请求
```

- 结果：统一字典 = 基础 18 + 15 = 33 字段（见数据字典）。
- 注意：OTA 传输专有字段（seq/CRC/验签/pending/health_deadline）**不**在此列，见 ADR-006。
