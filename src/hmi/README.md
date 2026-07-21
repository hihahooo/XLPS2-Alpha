# HMI — 安卓应用（React + Vite + TS）

> 全新脚手架。**不复用**历史代码；仅沿用 NP@XLPS2 知识库中沉淀的可落地思路。

## 职责

现场操作员交互：设备监控、任务下发、状态可视化、参数配置、告警处理。

## 技术栈

- React + Vite + TypeScript
- 状态管理：Zustand
- 打包：Capacitor（生成 Android apk）
- 通信：MQTT（断线重连）
- 鉴权：JWT HS256，三角色 RBAC（操作员 / 维护 / 管理员）

## 四功能模块

1. 设备总览（实时状态、current_state）
2. 任务管理（下发 / 暂停 / 取消）
3. 参数配置（受 RBAC 约束）
4. 诊断与告警（四级容错可视化）

## 目录（建议）

```
src/hmi/
  app/         # Capacitor 壳
  src/
    modules/   # 四功能模块
    store/     # Zustand
    mqtt/      # MQTT 客户端 + 重连
    auth/      # JWT / RBAC
  android/     # Capacitor 输出
```

## 开发说明

- 所有展示字段遵循 `config/data_dictionary.json`（SSOT）。
- MQTT 断线重连须保证 QoS1 至少一次投递。
- RBAC：配置/固件相关操作仅管理员可见。
