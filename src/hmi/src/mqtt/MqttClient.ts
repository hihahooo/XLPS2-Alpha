/**
 * MQTT 客户端封装（mqtt.js over WebSocket）。
 *
 * 关键特性（满足 SSOT/治理要求）：
 *  - 主题严格使用 rgv/{devId}/{topic}（见 topics.ts）。
 *  - QoS1（至少一次）投递；clean=false 会话保持，断线重订阅。
 *  - 断线指数退避重连（reconnectBaseMs → reconnectMaxMs，×2 倍增）。
 *  - 离线缓存：未连接时发布进有界队列，重连后冲刷（结合 QoS1 最终一致）。
 *
 * 注意：mqtt.js 在浏览器/安卓 WebView 走 WebSocket；broker 须开启 ws/wss 监听。
 */
import mqtt, { type MqttClient as RawClient } from 'mqtt';
import { APP_CONFIG } from '../config';
import { HMI_SUBSCRIBE, topicFor, type TopicName } from '../contract/topics';

export type ConnStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

export interface MqttHandlers {
  onStatus?: (s: ConnStatus, info?: { attempt?: number; error?: string }) => void;
  onMessage?: (topic: string, payload: unknown) => void;
}

interface QueuedMsg {
  topic: string;
  payload: string;
  qos: 0 | 1 | 2;
}

const MAX_QUEUE = 256;

export class MqttClient {
  private client: RawClient | null = null;
  private devId: string;
  private handlers: MqttHandlers;
  private status: ConnStatus = 'disconnected';
  private attempt = 0;
  private backoffMs = APP_CONFIG.mqtt.reconnectBaseMs;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private offlineQueue: QueuedMsg[] = [];
  private closedByUser = false;

  constructor(devId: string, handlers: MqttHandlers) {
    this.devId = devId;
    this.handlers = handlers;
  }

  getStatus(): ConnStatus {
    return this.status;
  }

  private setStatus(s: ConnStatus, info?: { attempt?: number; error?: string }) {
    this.status = s;
    this.handlers.onStatus?.(s, info);
  }

  connect(): void {
    this.closedByUser = false;
    if (this.client) return;
    this.setStatus('connecting');
    const opt = {
      username: APP_CONFIG.mqtt.username || undefined,
      password: APP_CONFIG.mqtt.password || undefined,
      keepalive: APP_CONFIG.mqtt.keepalive,
      clean: APP_CONFIG.mqtt.clean,
      reconnectPeriod: 0, // 自定义指数退避（禁用内置重连）
      connectTimeout: 10000,
      clientId: `hmi_${this.devId}_${Math.random().toString(16).slice(2, 10)}`,
    };
    const c = mqtt.connect(APP_CONFIG.mqtt.brokerUrl, opt);
    this.client = c;

    c.on('connect', () => this.onConnect());
    c.on('message', (t: string, buf: Buffer) => this.onMessage(t, buf));
    c.on('error', (e: Error) => this.onError(e));
    c.on('close', () => this.onClose());
    c.on('offline', () => {
      if (this.status === 'connected') this.setStatus('reconnecting', { attempt: this.attempt });
    });
  }

  private onConnect() {
    this.attempt = 0;
    this.backoffMs = APP_CONFIG.mqtt.reconnectBaseMs;
    this.setStatus('connected');
    for (const name of HMI_SUBSCRIBE) {
      this.client!.subscribe(topicFor(this.devId, name), { qos: 1 });
    }
    // 冲刷离线队列（QoS1 最终一致）
    const q = this.offlineQueue;
    this.offlineQueue = [];
    for (const m of q) this.client!.publish(m.topic, m.payload, { qos: m.qos });
  }

  private onMessage(topic: string, buf: Buffer) {
    let payload: unknown;
    const text = buf.toString('utf8');
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
    this.handlers.onMessage?.(topic, payload);
  }

  private onError(e: Error) {
    this.setStatus('error', { error: e.message });
  }

  private onClose() {
    if (this.closedByUser) {
      this.setStatus('disconnected');
      return;
    }
    this.scheduleReconnect();
  }

  private scheduleReconnect() {
    this.attempt++;
    this.setStatus('reconnecting', { attempt: this.attempt });
    const delay = Math.min(this.backoffMs, APP_CONFIG.mqtt.reconnectMaxMs);
    this.backoffMs = Math.min(this.backoffMs * 2, APP_CONFIG.mqtt.reconnectMaxMs);
    this.reconnectTimer = setTimeout(() => {
      if (this.closedByUser || !this.client) return;
      this.client.reconnect();
    }, delay);
  }

  /** 发布到指定主题（operator→device / hmi→cloud / 双向）。未连接时进离线队列。 */
  publish(name: TopicName | string, payload: unknown, qos: 0 | 1 | 2 = 1): boolean {
    const topic = topicFor(this.devId, name);
    const data = typeof payload === 'string' ? payload : JSON.stringify(payload);
    if (this.status !== 'connected' || !this.client) {
      if (this.offlineQueue.length < MAX_QUEUE) {
        this.offlineQueue.push({ topic, payload: data, qos });
      }
      return false;
    }
    this.client.publish(topic, data, { qos });
    return true;
  }

  disconnect(): void {
    this.closedByUser = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.client?.end(true);
    this.client = null;
    this.setStatus('disconnected');
  }

  setDevId(devId: string): void {
    this.devId = devId;
  }
}
