# HMI 安卓应用 · 开发文档（XLPS2-Alpha 全新基线）

> 全新脚手架，**不复用** `NP@XLPS2` 历史代码；仅沿用其沉淀的可落地思路。
> 所有契约以仓库 `config/`（数据字典 33 字段 / MQTT 主题 10 个）与 `docs/contract/`（ADR-001~007）为唯一事实源（SSOT）。

## 1. 职责

现场操作员交互：设备监控、任务下发、参数配置、干扰点管理、诊断/审计、OTA 触发。**不承载业务逻辑**（业务在 CFW）。HMI 仅做呈现与指令转发。

## 2. 技术栈

- React 18 + Vite 5 + TypeScript 5
- 状态管理：Zustand（四模块共享设备连接态与遥测）
- 打包：Capacitor 6（生成 Android apk，webDir=dist）
- 通信：MQTT over WebSocket（mqtt.js），QoS1 至少一次，断线指数退避重连 + 离线缓存
- 鉴权：JWT HS256（Web Crypto HMAC-SHA256）+ 三角色 RBAC（operator / engineer / admin）
- 体验：深色主题、手套操作友好（≥44px 触控目标）

## 3. 目录结构（实际产出）

```
src/hmi/
├─ package.json / vite.config.ts / tsconfig.json / tsconfig.node.json
├─ index.html / capacitor.config.ts
├─ .eslintrc.cjs / .prettierrc.json / .prettierignore / .gitignore
├─ src/
│  ├─ main.tsx / App.tsx / router.tsx / index.css / vite-env.d.ts
│  ├─ config.ts                 # broker/devId/jwt 配置（可用 Vite env 覆盖）
│  ├─ contract/                 # ★ SSOT 镜像（契约对齐核心）
│  │  ├─ types.ts               # 33 字段类型 + current_state 解码(ADR-003) + 状态编码表
│  │  ├─ dataDictionary.ts      # 镜像 config/data_dictionary.json（33 字段元数据）
│  │  └─ topics.ts              # 镜像 config/mqtt_topics.json（10 主题 + HMI 发布/订阅矩阵）
│  ├─ auth/
│  │  ├─ rbac.ts                # 三角色 + 能力矩阵 + 路由最低角色
│  │  ├─ jwt.ts                 # HS256 sign/verify（crypto.subtle）
│  │  ├─ storage.ts / mockUsers.ts
│  │  └─ AuthContext.tsx        # useAuth() + AuthProvider(restore)
│  ├─ mqtt/
│  │  ├─ MqttClient.ts          # MQTT 客户端：指数退避重连 + 离线队列 + QoS1
│  │  └─ mqttService.ts         # 单例：消息→各 store 接线 + publish 门面
│  ├─ comm/
│  │  ├─ modbusTask.ts          # ADR-004 任务帧(FC=0x10,基址0x2000) + CRC16 + 传输抽象
│  │  └─ CommService.ts         # 双通道门面：dispatchTask/setParam/pushSmdl/triggerOta/...
│  ├─ store/                    # Zustand
│  │  ├─ authStore.ts / connectionStore.ts / telemetryStore.ts
│  │  ├─ configStore.ts / logStore.ts / interferenceStore.ts
│  ├─ components/               # Layout / RouteGuard / ConnBadge / StateTreeView / FieldTable / FaultBadge / ConfirmDialog
│  └─ pages/                    # 六功能模块
│     ├─ DashboardPage 设备总览（33 字段 + 三区域状态机）
│     ├─ TaskPage     任务下发（ADR-004 Modbus）
│     ├─ ConfigPage   参数配置（param/set + config/smdl + 恢复出厂）
│     ├─ DiagnosticsPage 诊断告警（fault_level / diag/log）
│     ├─ InterferencePage 干扰点管理（interference/sync Envelope）
│     ├─ AuditPage    审计日志（audit/log）
│     ├─ OtaPage      OTA 触发（ota/cmd/progress，RBAC:admin）
│     └─ LoginPage    登录
└─ tests/                       # Vitest 自检
   ├─ contract.test.ts          # decodeCurrentState 往返 + 0xFFFF + ESTOP + 33字段/10主题一致性 + Modbus帧
   └─ rbac.test.ts              # 三角色能力矩阵
```

## 4. 四/六功能模块映射

| 模块 | 页面 | 数据来源 / 下发通道 | 最低角色 |
|------|------|--------------------|----------|
| 设备总览 | DashboardPage | 订阅 `telemetry`（22 字段）+ `current_state` 解码 | operator |
| 任务下发 | TaskPage | 本地 RS485 Modbus（ADR-004）/ MQTT 透传 | operator |
| 参数配置 | ConfigPage | 下发 `param/set`、`config/smdl`、`factory_reset_req` | engineer（恢复出厂 admin） |
| 诊断告警 | DiagnosticsPage | `fault_level` + `diag/log` | operator |
| 干扰点管理 | InterferencePage | `interference/sync` Envelope 上行/下行 | engineer |
| 审计日志 | AuditPage | `audit/log` | operator |
| OTA 升级 | OtaPage | `ota/cmd` / 订阅 `ota/progress`·`ota/result` | admin |

## 5. 契约对齐

### 5.1 33 字段 → MQTT 主题（与 SSOT 逐字一致）

| topic | 字段数 | 字段 |
|-------|-------|------|
| `telemetry` | 22 | current_state, position_mm, speed_mm_s, battery_soc, track_id, task_status, task_progress_pct, fault_code, fault_level, motor_current_a, motor_temp_c, encoder_position, laser_status, photoelectric_state, top_state, sub_state, region, is_safe, command_in, heartbeat_ts, uptime_s, fw_version |
| `ota/progress` | 4 | ota_active_slot, ota_state, ota_progress_pct, ota_target_version |
| `ota/result` | 1 | ota_result |
| `config/smdl` | 3 | smdl_version, param_revision, smdl_revision |
| `interference/sync` | 1 | interference_count |
| `diag/log` | 1 | diag_code |
| `audit/log` | 1 | audit_seq |
| **合计** | **33** | — |

> 注：`param_revision` 在 SSOT 中归属 `config/smdl` 主题；HMI 经 `param/set` 触发热调后由 CFW 自增（ADR-007）。

### 5.2 10 主题 · HMI 发布/订阅矩阵

主题模式：`rgv/{devId}/{topic}`（devId 由路径承载，不进 payload）。方向语义 cloud=云端/operator，device=控制器，hmi=安卓 App。

| 主题 | SSOT 方向 | HMI 行为 | QoS |
|------|-----------|----------|-----|
| `telemetry` | device→cloud | **订阅**（写遥测 store + 心跳） | 1 |
| `ota/progress` | device→cloud | **订阅**（写 ota_* 字段） | 1 |
| `ota/result` | device→cloud | **订阅**（写 ota_result） | 1 |
| `diag/log` | device→cloud | **订阅**（写诊断日志） | 1 |
| `interference/sync` | device↔hmi/cloud | **订阅 + 发布**（双向） | 1 |
| `param/set` | cloud→device | **发布**（参数热调 / 恢复出厂） | 1 |
| `config/smdl` | cloud→device | **发布**（SMDL 下发） | 1 |
| `ota/cmd` | cloud→device | **发布**（OTA 触发，admin） | 1 |
| `ota/data` | cloud→device | **发布**（分块，admin，预留） | 1 |
| `audit/log` | hmi→cloud | **发布**（操作审计，自增 audit_seq） | 1 |

### 5.3 current_state 解码（ADR-003）

`current_state = (region << 14) | (top_state << 8) | sub_state`；`0xFFFF` = 未初始化。

- `region`：0=主业务区 / 1=能源管理区 / 2=安全监控区（最高优先级仲裁；`region=2 && top=ESTOP` → 全局急停）。
- 解码在 `contract/types.ts` 的 `decodeCurrentState()`，与 OTA `schema.py` 位运算逐字节一致；编码 `encodeCurrentState()` 互逆，供模拟/测试。
- 顶层/子状态命名编码表（`TOP_STATE_TABLE` / `SUB_STATE_TABLE`）见 `types.ts`，层级路径例：`主业务区.行走.距离校验`。

### 5.4 任务下发（ADR-004）

`buildModbusFrame()`：FC=0x10，保持寄存器基址 `0x2000`，5 寄存器 / 10 字节布局：
`task_id(u16) | task_type(u16) | task_target_pos_mm(int32 高低16位) | task_axis(u16)`，帧尾 CRC16-MODBUS。
轴标识：`1=D_00 行走伺服` / `2=D_01 顶升伺服`。传输经 `ModbusTransport` 抽象，默认 `MockModbusTransport`（演示回 ACK），可替换为 `WebSerialModbusTransport` 或 Capacitor 串口插件。

## 6. RBAC 矩阵（三角色）

能力累进：operator ⊂ engineer ⊂ admin。

| 能力 | operator | engineer | admin |
|------|:--:|:--:|:--:|
| telemetry.view / task.dispatch / diag.view / audit.view / audit.publish | ✓ | ✓ | ✓ |
| interference.edit / config.param / config.smdl | — | ✓ | ✓ |
| ota.trigger / system.factory_reset | — | — | ✓ |

- 路由守卫：`components/RouteGuard.tsx`（`RequireAuth` / `RequireRole`），按 `ROUTE_MIN_ROLE` 拦截；侧边栏按角色显隐。
- 敏感操作（恢复出厂 / OTA 触发）二次确认弹窗 + 仅 admin 可见可点。
- JWT HS256：登录本地校验（演示用户表）→ 本地签发；启动 `restore()` 校验签名/过期还原会话。生产应改为向认证服务器登录取得 token。

## 7. 通信架构

- **双通道**：本地 RS485 Modbus（任务下发）/ 远程 MQTT（其余所有）。
- **重连**：`MqttClient` 禁用内置重连，自定义指数退避（1s→30s，×2 倍增），`clean=false` 会话保持，重连后自动重订阅 5 个上行主题。
- **离线缓存**：未连接时发布进有界队列（256），重连后冲刷；结合 QoS1 保证最终一致。
- **心跳**：`telemetry.heartbeat_ts` 写入 `connectionStore.lastHeartbeat`，顶栏实时显示连接态与重连次数。

## 8. 构建与出包

```bash
cd src/hmi
npm install
npm run dev        # 本地开发 http://localhost:5173
npm run build      # vite 构建 → dist/（Capacitor webDir）
npm run typecheck  # tsc --noEmit
npm test           # vitest 契约自检（decode + 33字段/10主题 + Modbus + RBAC）
npm run lint       # eslint
npm run format     # prettier
# 出安卓 apk：
npx cap add android   # 生成 android/（需 Android SDK）
npx cap sync          # 同步 dist → android
# 再用 Android Studio / gradle 打包 apk
```

`capacitor.config.ts` 已配 `appId=com.xlps2.hmi`、`webDir=dist`、`server.androidScheme=https`（满足 `crypto.subtle` 安全上下文）。

## 9. 测试（Vitest 自检）

- `tests/contract.test.ts`：current_state 编解码往返 + 0xFFFF 哨兵 + ESTOP 仲裁；**33 字段 / 10 主题与 SSOT JSON 逐字一致**；Modbus 帧结构 + CRC 自校验 + int32 拆分。
- `tests/rbac.test.ts`：三角色能力矩阵。
- 目标：本地 `npm test` 全绿；跨模块门禁 `tests/test_cross_module.py`（48/48）由主理人统一运行。

## 10. 跨模块待决歧义（需主理人裁定）

1. **current_state 命名状态数值编码**：位布局已严格对齐 ADR-003，但 `TOP_STATE_TABLE` / `SUB_STATE_TABLE` 中每个命名 top_state / sub_state 的**具体编号**需与 OTA 的 `schema.py` 逐字节统一（避免 HMI 与云端状态路径显示不一致）。建议主理人确认一份编号对照表写入 SSOT。
   - **位域重叠（已修复对齐，待 SSOT 确认）**：ADR-003 公式 `(region<<14)|(top_state<<8)|sub_state` 中，region 占 bits 14-15，恰为 top_state 字节（bits 8-15）的高 2 位，二者**重叠**。若 top_state 取 8 位，region≠0 时无法还原 top_state。HMI 据此将 top_state 解码为 **6 位（bits 8-13，掩码 0x3F）**、编码时 `top_state & 0x3F`；所有命名状态编号均 ≤ 0x3F，故与门禁公式 `(2<<14)|(5<<8)|3 == 0x8503` 逐字节一致。建议主理人在 ADR-003 中明确 top_state 为 6 位（或调整位布局消除重叠）。
2. **ADR-001 扩展字段 vs 33 字典归属**：ADR-001 列出的扩展意图字段（如 `task_id` / `task_target_pos_mm` / `task_axis` / `factory_reset_req` / `param_version` 等）未全部进入 33 字段数据字典。HMI 任务下发用 `task_id`/`task_target_pos_mm`/`task_axis`（ADR-004，走本地 Modbus），恢复出厂用 `factory_reset_req`（经 `param/set` 透传），参数版本以字典的 `param_revision` 为准。请主理人裁定这些"意图字段"与 33 字典的归属，消除重复/歧义。
3. **任务下发的远程 MQTT 通道**：10 主题中无显式 `task/cmd`。HMI 任务下发默认走本地 Modbus（ADR-004）；远程下发目前以 `telemetry` 附 `command_in` 透传占位。若需标准远程任务主题，请主理人裁定是否扩展第 11 主题或复用现有主题。
4. **interference Envelope 与字典**：字典仅含 `interference_count`（计数），而 `interference/sync` 负载 Envelope（`points:[{position_mm,confirmed,hit_count}]`）来自 ADR-002 负载描述。请主理人确认 Envelope 字段是否纳入字典，或保持为 MQTT 负载内部结构（类比 ADR-006「OTA 私有字段不进字典」）。

> 上述歧义不影响 HMI 本地构建与 33/10 主题覆盖；HMI 已对 SSOT 做镜像 + 测试守卫，待主理人裁定后同步更新。
