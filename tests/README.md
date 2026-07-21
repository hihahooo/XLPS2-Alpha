# XLPS2-Alpha — 跨模块联调门禁

本门禁验证四模块（CFW / EHW / HMI / OTA）之间的契约一致性，是 WP12 端到端验收的前置关卡。

- 数据字典字段数 = 33（TBD：由 config/data_dictionary.json 提供）
- MQTT Topic 数 = 10（TBD：由 config/mqtt_topics.json 提供）
- current_state 编码遵循 ADR-003
- OTA A/B 双分区遵循 ADR-005
- 四级容错遵循 ADR-006

设计目标：48 项断言全部通过（48/48）。下方为骨架，字段/主题/枚举的具体定义来自仓库内 config/ 契约 artifacts（由 SSOT 治理统一维护）。

## 运行

```bash
pip install -r requirements.txt   # pytest
pytest tests/test_cross_module.py -v
```
