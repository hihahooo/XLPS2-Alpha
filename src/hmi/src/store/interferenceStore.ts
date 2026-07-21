/**
 * 干扰点库状态（Zustand）——以 position_mm 为索引（见 overview）。
 * 远端 interference/sync 到来时 mergeRemote；本地编辑后由 CommService 发布上行。
 */
import { create } from 'zustand';

export interface InterferencePoint {
  position_mm: number;
  confirmed: boolean;
  hit_count: number;
}

export interface InterferenceTrack {
  track_id: number;
  points: InterferencePoint[];
}

interface InterferenceStore {
  tracks: Record<number, InterferenceTrack>;
  mergeRemote: (payload: unknown) => void;
  upsertPoint: (trackId: number, point: InterferencePoint) => void;
  removePoint: (trackId: number, position_mm: number) => void;
  reset: () => void;
}

function mergeTrack(tracks: Record<number, InterferenceTrack>, t: InterferenceTrack) {
  const existing = tracks[t.track_id]?.points ?? [];
  const byPos = new Map<number, InterferencePoint>();
  for (const p of existing) byPos.set(p.position_mm, p);
  for (const p of t.points) byPos.set(p.position_mm, p);
  tracks[t.track_id] = { track_id: t.track_id, points: [...byPos.values()] };
}

export const useInterferenceStore = create<InterferenceStore>((set) => ({
  tracks: {},
  mergeRemote: (payload) =>
    set((st) => {
      const tracks = { ...st.tracks };
      if (payload && typeof payload === 'object') {
        const p = payload as Record<string, unknown>;
        if (typeof p.track_id === 'number' && Array.isArray(p.points)) {
          mergeTrack(tracks, p as unknown as InterferenceTrack);
        } else if (Array.isArray(p.tracks)) {
          for (const t of p.tracks as InterferenceTrack[]) mergeTrack(tracks, t);
        }
      }
      return { tracks };
    }),
  upsertPoint: (trackId, point) =>
    set((st) => {
      const tracks = { ...st.tracks };
      const existing = tracks[trackId]?.points ?? [];
      const byPos = new Map<number, InterferencePoint>();
      for (const p of existing) byPos.set(p.position_mm, p);
      byPos.set(point.position_mm, point);
      tracks[trackId] = { track_id: trackId, points: [...byPos.values()] };
      return { tracks };
    }),
  removePoint: (trackId, position_mm) =>
    set((st) => {
      const tracks = { ...st.tracks };
      const existing = tracks[trackId]?.points ?? [];
      tracks[trackId] = {
        track_id: trackId,
        points: existing.filter((p) => p.position_mm !== position_mm),
      };
      return { tracks };
    }),
  reset: () => set({ tracks: {} }),
}));
