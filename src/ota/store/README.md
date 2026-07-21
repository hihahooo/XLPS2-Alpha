# 固件仓库（Firmware Store）

运行时由 `ota.store.FirmwareStore` 自动创建。每个版本落盘：

```
store/firmware/
  <version>.bin        # XLOT 封帧 blob（header+payload+SHA256+签名）
  <version>.meta.json  # 元数据（版本/类型/大小/SHA256/时间/备注）
```

- 发布强制**版本单调**（R4）：新版本须严格大于仓库内最大版本。
- 仓库不保管签名密钥；`FirmwareStore(signing_key=...)` 配置后 `get()` 会验签。
- 版本以十进制整数字符串承载于 SSOT `string` 字段（见 ota.versioning 设计决策）。
