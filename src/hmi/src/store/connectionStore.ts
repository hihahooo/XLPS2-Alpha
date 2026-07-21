/**
 * MQTT 连接状态（Zustand）——驱动顶栏连接指示、重连计数、心跳。
 */
import { create } from 'zustand';
import type { ConnStatus } from '../mqtt/MqttClient';

interface ConnectionStore {
  status: ConnStatus;
  attempt: number;
  lastError: string | null;
  connectedAt: number | null;
  lastHeartbeat: number | null;
  setStatus: (s: ConnStatus, info?: { attempt?: number; error?: string }) => void;
  setHeartbeat: (ts: number) => void;
}

export const useConnectionStore = create<ConnectionStore>((set) => ({
  status: 'disconnected',
  attempt: 0,
  lastError: null,
  connectedAt: null,
  lastHeartbeat: null,
  setStatus: (s, info) =>
    set((st) => ({
      status: s,
      attempt: info?.attempt ?? (s === 'connected' ? 0 : st.attempt),
      lastError: info?.error ?? (s === 'connected' ? null : st.lastError),
      connectedAt: s === 'connected' ? Date.now() : st.connectedAt,
    })),
  setHeartbeat: (ts) => set({ lastHeartbeat: ts }),
}));
