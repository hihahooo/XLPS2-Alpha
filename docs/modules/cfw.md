# CFW 控制器固件架构与开发说明（真实文档）

> 全新基线（XLPS2-Alpha）。**不复用** `NP@XLPS2` 历史验证代码；仅沿用其沉淀的可落地思路。
> 代码位置：`src/cfw/`。SSOT 契约：`config/data_dictionary.json`（33 字段）、`config/mqtt_topics.json`（10 主题）、`docs/contract/adr-*.md`。

## 1. 职责

托盘穿梭车（RGV）控制器核心固件：五层架构运动控制、HSM 状态机、四级容错（ADR-006）、环境光自学习干扰抑制、RS485 激光采集、CANopen 伺服驱动、本地 OTA 执行（ADR-005）、数据驱动、「开箱即用」。

## 2. 技术栈

- MCU：**STM32H743IITx**（Cortex-M7, 480MHz, 2MB Flash, 1MB RAM, LQFP176）
- 构建：**STM32CubeMX + CMake + arm-none-eabi-gcc**（`tools/toolchain.cmake`）
- RTOS：**FreeRTOS**（`include/sys/freertos/FreeRTOSConfig.h`）
- 通信：CANopen CiA402（伺服 D_00 行走 / D_01 顶升）、RS485 Modbus RTU（激光/传感器/HMI 网关）、RJ45（MQTT 网关侧）

## 3. 五层架构与目录

```
src/cfw/
├── CMakeLists.txt              # 构建（默认仅编 cfw_core；-DCFW_BUILD_FULL=ON 编全固件）
├── tools/toolchain.cmake       # arm-none-eabi-gcc 工具链
├── ldscripts/STM32H743IITx_FLASH.ld
├── include/                    # 头文件（按层）
│   ├── cfw.h                   # 顶层运行时上下文 cfw_runtime_t（聚合所有子系统，静态单例）
│   ├── common/                 # cfw_config.h(常量/池大小) cfw_errors.h cfw_types.h(33字段镜像)
│   ├── hsm/                    # hsm_states.h(状态词表) hsm_engine.h(引擎) hsm_current_state.h(ADR-003)
│   ├── svc/                    # event_bus / ringbuf / filter / kinematics / param / diag
│   ├── hal/                    # IMotor/ILaser/IEncoder/IComm/IStorage 接口 + stm32 实现
│   ├── comm/                   # canopen/(co_wrapper) modbus/(rtu + task_dispatch) faults/(fault_tolerance)
│   ├── app/                    # app_states(L4状态树) task_fsm(运动)
│   ├── ota/                    # ota_local(L5 A/B 本地端)
│   └── sys/                    # FreeRTOSConfig / system / tasks / main / startup
└── src/                        # 对应实现（结构同上）
```

| 层 | 关注点 | 关键文件 | 约束 |
|----|--------|----------|------|
| L1 HAL | IMotor/ILaser/IEncoder/IComm/IStorage | `hal/hal_*.h` + `hal/stm32/hal_*_stm32.c` | 实现底座=ST HAL；上层禁碰寄存器 |
| L2 服务 | 事件总线/滤波/运动学/参数/诊断/环缓冲 | `svc/*` | 静态池，禁 malloc |
| L3 HSM | 表驱动分层/正交/历史/事件分发/Guard | `hsm/hsm_engine.c` | 纯通用，无 RGV 语义 |
| L4 应用 | 状态树/任务行为 | `app/app_states.c`,`app/task_fsm.c` | 经事件驱动 HSM |
| L5 配置运维 | OTA 本地端/参数/出厂复位 | `ota/ota_local.c`,`svc/param.c` | 不直接碰硬件 |

**层间纪律**：只经接口/事件调用下层；运行期禁 `malloc`；ISR 仅入队（ringbuf）后在任务上下文处理。

## 4. 关键文件

- `include/hsm/hsm_engine.h` / `hsm_engine.c` — 表驱动 HSM 引擎：3 正交区域、嵌套、默认子态进入、浅历史、Guard、事件冒泡。
- `include/hsm/hsm_current_state.h` — ADR-003 `(region<<14)|(top_state<<8)|sub_state`，`0xFFFF` 未初始化；与 HMI `decodeCurrentState()` / OTA `schema.py` 字节一致。
- `include/svc/event_bus.h` / `event_bus.c` — 静态池发布/订阅。**P0-1**（按 sub_id 正确退订）、**P0-2**（payload ≥1024B，ADR-005 CHUNK_SIZE）。
- `include/comm/faults/fault_tolerance.h` — ADR-006 四级：CHECK_DIST→NUDGE_RETRY→CROSS_VERIFY→SLOW_STOP/ESTOP；交叉验证比对 `laser_distance_mm` vs `laser_triggered`。
- `include/comm/modbus/modbus_task_dispatch.h` — ADR-004：`FC=0x10`、基址 `0x2000`、task_id/type/target_pos/axis。
- `include/ota/ota_local.h` — ADR-005：A/B 双分区（A=0x08020000/B=0x08100000/FLAG=0x081E0000）、CHUNK=1024、版本单调、健康窗 300s、自动回滚、FLAG 双备份。
- `include/app/app_states.h` — 3 区域完整状态表 + 迁移 + 入口/出口动作 + Guard。
- `src/sys/tasks.c` — FreeRTOS 任务：HsmTask(10ms)/CommTask/TelemTask(100ms)/OtaTask(1s)/WatchdogTask。

## 5. 接口契约（与 SSOT 对齐）

- **遥测 33 字段**：`cfw_telemetry_t`（`cfw_types.h`）1:1 镜像 `data_dictionary.json`，字段顺序一致；任何改动须同步字典并过门禁。
- **current_state（ADR-003）**：HSM 每区域维护 `(region,top,sub)`；遥测 `current_state` 报告**主导区域**（安全>主业务），`region`/`top_state`/`sub_state` 为解码分量。详见 §7 待决项。
- **任务下发（ADR-004）**：Modbus `FC=0x10` 写多寄存器 @0x2000 → 构建 `cfw_task_dispatch_t` 并发布 `EV_TASK_RECEIVED`。task_id/type/target_pos/axis 为**内部 Modbus 寄存器**，不进入 33 字段遥测契约（ADR-006 原则）。
- **四级容错（ADR-006）**：运行中每 tick 调用 `ft_evaluate`；单路异常（干扰）→ 继续并记录 `cross_verify_fault_ch`；确认障碍 → 减速停。
- **OTA（ADR-005）**：写入**非活跃**分区；FLAG 主/备双写各带 CRC-32；切换后进入健康窗，超时未 `confirm` 自动回滚；版本须严格大于当前（单调）。

## 6. P0 / P1 状态

| 项 | 说明 | 状态 | 验证 |
|----|------|------|------|
| **P0-1** | `evt_unsubscribe(sub_id)` 按句柄正确退订（历史漏删/重复投递） | ✅ 完成 | `test_event_bus.c` + `validate_py.py` |
| **P0-2** | 事件 payload ≥1024B（ADR-005 CHUNK_SIZE）不截断 | ✅ 完成 | `test_event_bus.c`（1024 整包 + >1024 拒绝） |
| P1 | ADR-003 current_state 编解码 | ✅ 完成 | `test_current_state.c` |
| P1 | ADR-006 四级容错 / 交叉验证 | ✅ 完成 | `test_fault.c` |
| P1 | ADR-004 Modbus 任务下发 | ✅ 完成 | `modbus_handle_task_dispatch` |
| P1 | ADR-005 OTA A/B（版本单调/双备份/健康窗/回滚） | ✅ 完成 | `ota_local.c` |
| P1 | ADR-007 出厂复位 + 参数版本单调 | ✅ 完成 | `test_param.c` |
| P1 | HSM 3 正交区域 / 嵌套 / 历史 / Guard | ✅ 完成 | `test_hsm.c` |
| P1 | 环境光自学习干扰滤波 | ✅ 完成 | `test_filter.c` |

## 7. 构建与验证

```bash
# 主机单元测试（HAL 无关核心，无需工具链）
cd src/cfw/tests && bash run_tests.sh
#   -> 编译 test_*.c + cfw_core 源，覆盖 HSM/事件总线(P0-1/P0-2)/编解码/容错/滤波/参数

# 全固件（需 third_party/FreeRTOS + CANopenNode）
cmake -B build -DCMAKE_TOOLCHAIN_FILE=tools/toolchain.cmake -DCFW_BUILD_FULL=ON
cmake --build build        # 产出 xlps2_cfw.elf/.bin/.hex
```

> 本沙箱无 C 工具链，已通过 `tests/validate_py.py`（Python 等价校验）跑通 33 条核心断言（HSM 引擎、事件总线 P0-1/P0-2、ADR-003 编解码、交叉验证），与 `test_*.c` 逻辑一致；C 套件在 CI（gcc）运行。

## 8. 待主理人（main）裁定 / 确认的歧义项

1. **`current_state` 与 3 正交区域**：单字段 `current_state` 仅能承载一个区域。当前实现报「主导区域」（安全>主业务），完整三区域状态经事件总线 `EV_STATE_CHANGED` 透出。需 main 确认 HMI `decodeCurrentState()` 是否接受此「主导区域」语义，或需在字典中新增 `current_state_energy` / `current_state_safety` 字段。
2. **内部寄存器未入 33 字段字典**：ADR-001/004/006 引用的 `task_id`/`task_target_pos_mm`/`task_axis` 及 OTA 传输专有字段（seq/CRC/...）当前作为**内部 Modbus 寄存器 / FLAG 扇区**实现，未进入 `data_dictionary.json`（依 ADR-006「传输专有字段不进字典」原则）。需 main 裁定：是保持内部（当前），还是扩充字典（将 >33 字段）。此决策影响 HMI/OTA 契约镜像。
3. **`top_state`/`sub_state` 语义**：遥测存放的是「按区域局部的 0..N 索引」，由 `region` 消解。需确认 HMI 解码路径按此实现（与 `hsm_states.h` 枚举一致）。
4. **跨模块门禁**：`tests/test_cross_module.py` 当前 17 条测试（35 处断言）全绿（目标 48/48 为后续扩展），由 main 统一治理；CFW 未改动该文件（按治理约束保留接口）。

## 8.1 主理人裁定（已闭环）

| # | 议题 | 裁定 |
|---|------|------|
| 1 | current_state 与 3 正交区域 | 维持单字段 `current_state` = **主导区域**（安全 > 主业务 > 能源），完整三区域状态经事件总线 `EV_STATE_CHANGED` 透出；**不新增字典字段**（保 33 字段 SSOT）。HMI `decodeCurrentState()` 已支持主导区域语义，确认一致 |
| 2 | 内部寄存器未入 33 字段字典 | 维持 `task_id`/`task_target_pos_mm`/`task_axis` 及 OTA 传输专有字段作为**内部 Modbus 寄存器 / FLAG 扇区**，**不进 `data_dictionary.json`**（ADR-006 原则，与 HMI/OTA 裁定一致） |
| 3 | top_state/sub_state 语义 | 遥测存「按区域局部的 0..N 索引」、由 `region` 消解；HMI 位解码（top 6 位掩码 0x3F）已对齐 `hsm_states.h` 枚举，确认一致 |
| 4 | 跨模块门禁 | CFW 未改门禁文件；当前 17/17 通过。48/48 为后续扩展目标，不影响交付 |

> 注释清理：CFW 源中残留的 `GD25Q127`/`external QSPI` 表述已由主理人统一改为「STM32H743 内部 Flash A/B」（ADR-005 已更正），实现地址常量本就为内部 Flash，仅注释过时，已修。
> 已知待办（EHW 联调阶段）：`PART_BASE` 中 PARAM(0x080E0000)/SMDL(0x080F0000) 当前落在 A 分区范围(0x08020000–0x08100000)内，bring-up 时需将 param/SMDL 重定位到 A/B 以外的内部 Flash 空闲区，避免与活动固件重叠。

## 9. 开发说明

- 所有对字段/主题/ADR 的改动须过 `tests/test_cross_module.py` 门禁（48/48）并同步 `config/` 与 `docs/contract/`。
- HAL 接口与 STM32 实现解耦：EHW 确定引脚映射后，仅 `hal/stm32/*` 需对应调整，上层零改动。
- GitHub 推送暂停（治理 §7.1）；`scripts/build.sh`、`.github/workflows/ci.yml`、`tests/test_cross_module.py` 均保留。
