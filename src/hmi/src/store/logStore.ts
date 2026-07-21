/**
 * 日志状态（Zustand）——audit/log（HMI 上报 + 云端回显）与 diag/log（设备诊断）环形缓冲。
 */
import { create } from 'zustand';

export interface LogEntry {
  id: number;
  ts: number;
  source: 'audit' | 'diag';
  seq?: number;
  payload: unknown;
}

const CAP = 200;
let seqCounter = 0;

interface LogStore {
  audit: LogEntry[];
  diag: LogEntry[];
  pushAudit: (payload: unknown) => void;
  pushDiag: (payload: unknown) => void;
  clear: () => void;
}

function nextId(): number {
  return ++seqCounter;
}

export const useLogStore = create<LogStore>((set) => ({
  audit: [],
  diag: [],
  pushAudit: (payload) =>
    set((st) => {
      const entry: LogEntry = { id: nextId(), ts: Date.now(), source: 'audit', payload };
      return { audit: [entry, ...st.audit].slice(0, CAP) };
    }),
  pushDiag: (payload) =>
    set((st) => {
      const entry: LogEntry = { id: nextId(), ts: Date.now(), source: 'diag', payload };
      return { diag: [entry, ...st.diag].slice(0, CAP) };
    }),
  clear: () => set({ audit: [], diag: [] }),
}));
