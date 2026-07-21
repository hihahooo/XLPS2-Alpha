/**
 * MQTT 服务单例——把底层 MqttClient 与各个 Zustand store 接线。
 *  - telemetry / ota/progress / ota/result / diag/log / audit/log → 写入对应 store
 *  - 心跳 heartbeat_ts → connectionStore
 *  - interference/sync（来自设备/云端）→ interferenceStore
 *  - 暴露 publish() 供 CommService/页面下发（operator→device / hmi→cloud）
 */
import { MqttClient } from './MqttClient';
import { useConnectionStore } from '../store/connectionStore';
import { useTelemetryStore } from '../store/telemetryStore';
import { useLogStore } from '../store/logStore';
import { useConfigStore } from '../store/configStore';
import { useInterferenceStore } from '../store/interferenceStore';
import type { TopicName } from '../contract/topics';

class MqttService {
  private client: MqttClient | null = null;

  private ensure(): MqttClient {
    if (this.client) return this.client;
    const devId = useConfigStore.getState().devId;
    this.client = new MqttClient(devId, {
      onStatus: (s, info) => useConnectionStore.getState().setStatus(s, info),
      onMessage: (topic, payload) => this.onMessage(topic, payload),
    });
    return this.client;
  }

  connect(): void {
    const c = this.ensure();
    if (c.getStatus() === 'disconnected') c.connect();
  }

  private onMessage(topic: string, payload: unknown): void {
    const name = topic.slice(topic.lastIndexOf('/') + 1);
    if (!payload || typeof payload !== 'object') return;
    const data = payload as Record<string, unknown>;
    const tel = useTelemetryStore.getState();
    const logs = useLogStore.getState();
    const conn = useConnectionStore.getState();

    // 字段过滤写入遥测（ota_*, diag_code, audit_seq 等均在 33 字段内）
    tel.apply(data);
    const hb = data.heartbeat_ts;
    if (typeof hb === 'number') conn.setHeartbeat(hb);

    if (name === 'diag/log') logs.pushDiag(payload);
    else if (name === 'audit/log') logs.pushAudit(payload);
    else if (name === 'interference/sync') useInterferenceStore.getState().mergeRemote(payload);
  }

  publish(name: TopicName | string, payload: unknown, qos: 0 | 1 | 2 = 1): boolean {
    return this.ensure().publish(name, payload, qos);
  }

  disconnect(): void {
    this.client?.disconnect();
  }

  /** 切换设备：断开并以新 devId 重建（若原已连接则自动重连） */
  setDevId(devId: string): void {
    const wasConnected = this.client?.getStatus() === 'connected';
    this.client?.disconnect();
    this.client = null;
    useConfigStore.getState().setDevId(devId);
    if (wasConnected) this.connect();
  }
}

export const mqttService = new MqttService();
