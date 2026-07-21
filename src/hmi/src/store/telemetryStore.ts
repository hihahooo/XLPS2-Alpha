/**
 * 遥测状态（Zustand）——33 字段最新快照 + 近期历史环形缓冲。
 * 仅承载展示数据，不在此做业务决策（业务在 CFW）。
 */
import { create } from 'zustand';
import type { Telemetry } from '../contract/types';
import { FIELD_NAMES } from '../contract/dataDictionary';

const FIELD_SET = new Set<string>(FIELD_NAMES);
const HISTORY_CAP = 120;

interface Sample {
  ts: number;
  sample: Telemetry;
}

interface TelemetryStore {
  latest: Telemetry;
  updatedAt: number | null;
  history: Sample[];
  apply: (data: Record<string, unknown>) => void;
  reset: () => void;
}

export const useTelemetryStore = create<TelemetryStore>((set) => ({
  latest: {},
  updatedAt: null,
  history: [],
  apply: (data) => {
    const merged: Telemetry = {};
    for (const k of Object.keys(data)) {
      if (FIELD_SET.has(k)) {
        (merged as Record<string, unknown>)[k] = data[k];
      }
    }
    if (Object.keys(merged).length === 0) return;
    set((st) => {
      const latest = { ...st.latest, ...merged };
      const history = [...st.history, { ts: Date.now(), sample: merged }].slice(-HISTORY_CAP);
      return { latest, updatedAt: Date.now(), history };
    });
  },
  reset: () => set({ latest: {}, updatedAt: null, history: [] }),
}));
