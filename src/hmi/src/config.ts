/**
 * 应用运行配置。可经 Vite 环境变量（.env）覆盖，见 .gitignore（已忽略 .env）。
 */
export const APP_CONFIG = {
  mqtt: {
    // MQTT over WebSocket（broker 须开启 ws/wss 监听；ADR-005 建议 mqtts://emqx.np-xltech.com:8883）
    brokerUrl: import.meta.env.VITE_MQTT_URL ?? 'wss://emqx.np-xltech.com:8084/mqtt',
    username: import.meta.env.VITE_MQTT_USER ?? '',
    password: import.meta.env.VITE_MQTT_PASS ?? '',
    reconnectBaseMs: 1000,
    reconnectMaxMs: 30000,
    keepalive: 30,
    clean: false, // 会话保持（断线重订阅 + 离线消息 QoS1）
  },
  auth: {
    // ⚠️ 仅演示用：真实环境由认证服务器签发 JWT，secret 绝不下发到客户端。
    jwtSecret: import.meta.env.VITE_JWT_SECRET ?? 'xlps2-alpha-dev-secret',
    tokenTtlSec: 8 * 3600,
  },
  defaultDevId: import.meta.env.VITE_DEVID ?? 'RGV-001',
  storageKeys: {
    token: 'xlps2.token',
    devId: 'xlps2.devId',
    theme: 'xlps2.theme',
  },
};
