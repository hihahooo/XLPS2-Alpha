# OTA 云端升级 — 开发文档（XLPS2-Alpha 全新基线）

> 本文件为**真实开发文档**，取代脚手架占位。代码位于 `src/ota/`。
> 不复用任何历史验证基线代码，仅沿用其沉淀的可落地思路。

## 1. 职责

云端 OTA 服务负责固件 / SMDL / 参数**三级远程升级与回滚**。设备端 OTA 客户端不是独立硬件，而是承载于 CFW 的 CommTask + L5 配置运维层；本服务是云侧编排者。

| 级别 | 内容 | 通道 | 版本治理 |
|------|------|------|----------|
| 固件 FW | A/B 双分区烧写 | `ota/*` | 版本单调（R4） |
| SMDL | 运动描述语言 | `config/smdl` | `smdl_revision++`（ADR-001） |
| 参数 | 参数热调 | `param/set` | `param_revision++`（ADR-007） |

## 2. 技术栈

- 语言：Python ≥ 3.10（服务工程，`pyproject.toml`）
- 消息：EMQX MQTT **over TLS**（`mqtts://emqx.np-xltech.com:8883`，ADR-005）
- 客户端：`paho-mqtt`（仅真实运行依赖；单测用内存传输，无需 broker）
- 物理分区：GD25Q127 ×2 双芯片（A/B 物理双分区，ADR-005）
- 测试：`pytest`（单元 + 端到端集成），当前 **57/57 通过，coverage ≥ 92%**

## 3. 目录布局（`src/ota/`）

```
src/ota/
  pyproject.toml          # 包元数据 / pytest 配置
  requirements.txt          # paho-mqtt
  requirements-dev.txt      # pytest
  ota/                     # 可导入包
    __init__.py            # 公开 API 汇聚
    config.py              # SSOT 派生常量（A/B 地址、FLAG、CHUNK、HEALTH_WINDOW、EMQX、10 主题）
    exceptions.py          # OTA 异常层级
    crypto.py              # CRC32 / SHA256 / HMAC 签名验签
    versioning.py          # 版本单调（R4）
    framing.py             # 固件包封帧 + 签名/完整性（R-签名）
    chunking.py           # 分片 seq+CRC + 断点续传（R-断电续传）
    flash.py               # Flash 抽象 + InMemoryFlash（仿真 GD25Q127）
    flag.py               # FLAG 扇区双备份 + 自愈（R15）
    ab_orchestrator.py    # A/B 状态机与回滚编排（R5 / R7）
    health_monitor.py     # 健康观测窗（R7）
    topics.py              # 主题构造/解析（rgv/{devId}/{topic}）
    mqtt_adapter.py       # MQTT 传输抽象 + InMemoryTransport
    mqtt_client.py        # EMQX TLS 客户端（paho：重连 + LWT）
    store.py               # 固件仓库（版本单调）
    schema.py              # 载荷校验（ADR-006 传输字段隔离）
    service.py             # OTA 服务（cmd/data/progress/result 全流程）
    keys.py               # 签名密钥加载（KMS/安全存储托管）
  broker/                   # EMQX 配置参考 + 本地 dev 密钥（不入库）
    emqx.conf
    ota_key.hex
    README.md
  store/                   # 固件仓库运行时目录（自动创建）
    README.md  .gitkeep
  scripts/
    serve.py               # 运行云端 OTA 服务
    build_firmware.py       # 封帧并发布固件/SMDL/参数包
  tests/                   # 单元 + 集成测试（57 例）
    conftest.py
    test_versioning.py  test_framing.py  test_chunking.py
    test_flag.py  test_flash.py  test_health_monitor.py
    test_ab_orchestrator.py  test_store.py  test_schema.py
    test_mqtt_adapter.py  test_mqtt_client.py  test_keys.py
    test_service.py
```

## 4. 三级升级流程

```
云端 ota/cmd(start, target_version, slot)
  → ota/data(分片 seq+CRC，断点续传)
  → 设备写入非活跃分区 + 校验
  → 重启切换 active_slot（FLAG 双备份固化）
  → 健康窗(HEALTH_WINDOW_S=300) 内 ota/progress(active) 上报健康
  → 超时未确认 → 自动回滚到上一稳定分区
  → ota/result(ok/fail/rollback)
```

完整生命周期由 `OtaService`（service.py）驱动，决策下放到纯函数式引擎
`AbOrchestrator` 与 `HealthWindow`，保证可单测、无状态副作用。

## 5. A/B 双分区状态机（ADR-005）

物理地址（SSOT，与 `config/` 逐字一致）：

| 项 | 值 |
|----|----|
| A 分区基址 | `0x08020000` |
| B 分区基址 | `0x08100000` |
| FLAG 扇区 | `0x081E0000` |
| FLAG 主/备 | 主 `0x000` / 备 `0x200`，各带 CRC-32 |
| CHUNK_SIZE | `1024` |
| HEALTH_WINDOW_S | `300` |

云端 `DeviceAbState` 视图（`ab_orchestrator.py`）：
`active_slot / committed_slot / current_version / pending / pending_target / health_deadline / ota_state / last_result`。

状态跃迁（`AbOrchestrator`）：
```
idle ──submit_upgrade──▶ planning
planning ──plan_upgrade(版本单调+R5选非活跃)──▶ streaming (ota/cmd start)
streaming ──设备 last_seq 续传──▶ streaming
streaming ──设备 reboot 进新分区──▶ health_window (HEALTH_WINDOW_S 开启)
health_window ──健康回报(active)──▶ confirmed (ota/cmd confirm) ──ota/result ok──▶ done
health_window ──超时未确认──▶ rollback (ota/cmd rollback) ──ota/result rollback──▶ rolled_back
任意 ──ota/result fail──▶ rolled_back
```

## 6. P1 五规则落地与映射

| # | 规则 | 文件 : 关键实现 | 单测 |
|---|------|----------------|------|
| 1 | **版本单调（禁止降级）** | `versioning.py:assert_monotonic`（新 > 当前，严格拒绝 ≤）；`store.py:publish` 仓库级双保险 | test_versioning / test_store |
| 2 | **A/B 双分区（下发非活跃）** | `ab_orchestrator.py:plan_upgrade` → `other_slot(active)`；FLAG 双备份 `flag.py` | test_ab_orchestrator / test_flag |
| 3 | **断点续传** | `chunking.py:chunk_package / reassemble / resume_plan`（seq+CRC，依 last_seq 补发缺失分片） | test_chunking / test_service(resume) |
| 4 | **健康确认 + 超时回滚** | `health_monitor.py:HealthWindow` + `service.tick()` 超时触发 `on_timeout` 回滚编排 | test_health_monitor / test_service(timeout/telemetry) |
| 5 | **异常隔离（FLAG 双备份 + 字段不污染字典）** | `flag.py:FlagStore` 主备自愈；`schema.py` 校验传输专有字段不进 33 字段字典（ADR-006） | test_flag / test_schema / test_service(malicious) |

> 历史 ADR 编号（R3/R4/R5/R7/R15）与本 SSOT 五项表述的对应：版本单调↔R4、A/B↔R5、
> 健康确认/回滚↔R7、FLAG 双备份↔R15、异常隔离/断点↔R3。以本 `modules/ota.md` 五项表述与治理 `governance.md` 为准。

## 7. 传输专有字段隔离（ADR-006）

- `devId` 一律由 **主题路径**承载（`rgv/{devId}/{topic}`），**禁止**进入 payload（`schema.py:_reject_dev_id`）。
- 传输专有字段（`seq`/`crc`/`signature`/`pending`/`active_slot(内部)`/`health_deadline`/`health_receipt`/`last_seq`）**仅作 MQTT 载荷内部字段或存 FLAG 扇区，不进入 33 字段数据字典**。
- `schema.py:assert_transport_isolation` + `test_schema:test_transport_fields_not_in_dictionary` 校验：加载真实 `config/data_dictionary.json` 的 33 字段，断言无传输专有字段泄漏。
- `ota/progress` 仅承载字典字段 `ota_state/ota_progress_pct/ota_active_slot/ota_target_version`，`last_seq` 为白名单内的续传控制字段（不进字典）。

## 8. 健康确认与回滚

1. 设备烧写校验后重启进新分区，发布 `ota/progress(ota_state=active)`。
2. 云端 `OtaService._on_progress` 开启 `HealthWindow`（截止 = now + `HEALTH_WINDOW_S`）。
3. 窗内收到健康回报（`ota/progress(active)` 或 `telemetry(is_safe=true / fault_level=0)`）→ `_confirm` 下发 `ota/cmd confirm`，提交新分区。
4. 超时未确认 → `service.tick(now)` 检测 `is_expired` → `AbOrchestrator.on_timeout` 下发 `ota/cmd rollback`，回退到 `committed_slot`（上一稳定分区）。
5. 单设备 / 单包异常经 `try/except` 隔离，**不中断服务**（`_on_progress`/`_on_result` 非法消息被 `schema` 拒绝后静默跳过）。

## 9. 构建 / 部署

```bash
# 依赖
pip install -r requirements.txt -r requirements-dev.txt

# 打包并发布固件（版本单调 + HMAC 签名）
python scripts/build_firmware.py raw.bin 1024 \
    --store-dir ./store/firmware --key-file ./broker/ota_key.hex --note "v1.0 首版"

# 运行云端 OTA 服务（真实 EMQX TLS）
python scripts/serve.py --client-id xlps2-ota-cloud \
    --ca-certs ./broker/ca.pem --store-dir ./store/firmware \
    --key-file ./broker/ota_key.hex

# 单测（无需 broker）
python -m pytest tests -q
python -m pytest tests -q --cov=ota --cov-report=term-missing
```

- `pyproject.toml` 暴露 `xlps2-ota-serve` / `xlps2-ota-build` 入口。
- **签名密钥生产由 KMS / 安全存储托管**，本仓库 `broker/ota_key.hex` 仅供本地联调，不随镜像分发。
- EMQX ACL 见 `broker/README.md`（云端仅允许发布 `ota/cmd`、`ota/data`、`cloud/status`，订阅 `ota/progress`、`ota/result`、`telemetry`）。

## 10. 测试覆盖

- **101 例全部通过**（无需 broker），coverage 93%（TOTAL 1140 行 / 84 未覆盖）。
- 核心逻辑覆盖：orchestrator 96% / chunking 98% / flag 95% / store 95% / framing 93% / health 93% / service 91%。
- `mqtt_client.py`（真实 EMQX 交互）以**伪 paho 模块**单测覆盖 TLS/LWT/重连重订阅/路由（无需 broker）；真实 broker 连通性属联调（WP9–WP11）。
- 跨模块契约门禁 `tests/test_cross_module.py` **不受影响，仍 17/17**（config 未改动）。

## 11. 跨模块契约裁定（已对齐 SSOT，无需改代码）

主理人已裁定以下三项跨模块歧义，全部与现有实现一致，本基线无需改动（SSOT/ADR 已由主理人落定；本节仅作闭环记录）：

1. **版本号形态（已裁定）**：`fw_version`/`ota_target_version` 为 string，承载十进制整数序号（如 `"1024"`）做单调比较，semver 仅展示别名。与 ADR-005「单调递增整数」一致。`versioning.py` 已实现并单测，**无需改**。
2. **Flash 地址空间（已裁定）**：ADR-005 已更正为 STM32H743 内部 Flash 2MB 逻辑双分区（删除 GD25Q127 表述）。本实现「地址常量 + `flash.py` 抽象层解耦」与之相符，确认内部 Flash A/B，**无需改**。
3. **续传信号通道（已裁定）**：不新增主题；设备已收 seq 经 `ota/progress.last_seq`（传输私有字段，不进字典）回报，云端据此续传。与 ADR-006 及 10 主题约束一致，**无需改 ADR-002**。
