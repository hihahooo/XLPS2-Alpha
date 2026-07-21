# OTA — 云端升级（Python + EMQX，全新基线）

> 开发文档见 [`../../../docs/modules/ota.md`](../../../docs/modules/ota.md)（流程、A/B 状态机、P1 五规则映射、构建/部署、待决歧义）。

## 职责

固件 / SMDL / 参数**三级远程升级与回滚**：版本单调、A/B 双分区、断点续传、健康确认与自动回滚、传输专有字段隔离。

## 技术栈

- Python ≥ 3.10（`pyproject.toml`）
- EMQX MQTT **over TLS**（`mqtts://emqx.np-xltech.com:8883`，ADR-005）
- 客户端 `paho-mqtt`（仅运行依赖；单测用 `mqtt_adapter.InMemoryTransport`，无需 broker）
- 物理分区 STM32H743IIT6 内部 Flash 逻辑双分区 A/B（ADR-005）

## 目录

```
src/ota/
  ota/            # 可导入包（config / versioning / framing / chunking / flash /
                   #  flag / ab_orchestrator / health_monitor / topics /
                   #  mqtt_adapter / mqtt_client / store / schema / service / keys）
  broker/          # EMQX 配置参考 + 本地 dev 密钥（不入库）
  store/           # 固件仓库运行时目录（自动创建）
  scripts/         # serve.py（运行服务）/ build_firmware.py（封帧发布）
  tests/           # 单元 + 集成测试（57 例，coverage ≥ 92%）
  pyproject.toml / requirements.txt / requirements-dev.txt
```

## 快速开始

```bash
pip install -r requirements.txt -r requirements-dev.txt

# 发布固件（版本单调 + HMAC 签名）
python scripts/build_firmware.py raw.bin 1024 \
    --store-dir ./store/firmware --key-file ./broker/ota_key.hex

# 运行云端服务（真实 EMQX TLS）
python scripts/serve.py --client-id xlps2-ota-cloud \
    --ca-certs ./broker/ca.pem --store-dir ./store/firmware \
    --key-file ./broker/ota_key.hex

# 单测（无需 broker）
python -m pytest tests -q
```

## P1 五规则（已逐条实现 + 单测）

| # | 规则 | 关键实现 |
|---|------|-----------|
| 1 | 版本单调（禁止降级） | `ota/versioning.py` + `ota/store.py` |
| 2 | A/B 双分区（非活跃下发） | `ota/ab_orchestrator.py` + `ota/flag.py` |
| 3 | 断点续传 | `ota/chunking.py` |
| 4 | 健康确认 + 超时回滚 | `ota/health_monitor.py` + `ota/service.py` |
| 5 | 异常隔离（FLAG 双备份 + 字段不污染字典） | `ota/flag.py` + `ota/schema.py` |

> 历史验证基线代码**不复用**；仅沿用其可落地思路。
