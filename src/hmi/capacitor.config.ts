import type { CapacitorConfig } from '@capacitor/core';

// Capacitor 配置：webDir 指向 Vite 构建产物 dist/，由 `npx cap add android` 生成 android/ 工程。
// 安卓端 MQTT 走 WebSocket（broker 须开启 ws/wss 监听），Capacitor 默认允许 https scheme。
const config: CapacitorConfig = {
  appId: 'com.xlps2.hmi',
  appName: 'XLPS2 HMI',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
};

export default config;
