# EMQX 配置（XLPS2-Alpha OTA）

云端 OTA 服务通过 **TLS** 连接 `mqtts://emqx.np-xltech.com:8883`（ADR-005）。

## 1. 监听与 TLS

```bash
# emqx.conf 关键项（示例，真实值由公司基础设施下发）
listeners.ssl.default.bind = 8883
listeners.ssl.default.certfile = /etc/emqx/certs/server.pem
listeners.ssl.default.keyfile  = /etc/emqx/certs/server.key
listeners.ssl.default.cacertfile = /etc/emqx/certs/ca.pem
```

## 2. 主题 ACL（最小权限）

云端客户端仅允许：
- 发布：`rgv/+/ota/cmd`、`rgv/+/ota/data`、`rgv/cloud/status`
- 订阅：`rgv/+/ota/progress`、`rgv/+/ota/result`、`rgv/+/telemetry`

设备客户端仅允许：
- 发布：`rgv/<devId>/ota/progress`、`rgv/<devId>/ota/result`、`rgv/<devId>/telemetry`
- 订阅：`rgv/<devId>/ota/cmd`、`rgv/<devId>/ota/data`

`devId` 一律由主题路径承载，禁止出现在 payload（治理 / ADR-002）。

## 3. 遗嘱（LWT）

云端连接配置遗嘱 `rgv/cloud/status`（`{"online":false}`），断线即通知运维。

## 4. 签名密钥

`ota_key.hex` 为 HMAC-SHA256 签名密钥（hex）。**生产由 KMS / 安全存储托管，
不入库、不随镜像分发**。本目录的 `ota_key.hex` 仅供本地联调。
