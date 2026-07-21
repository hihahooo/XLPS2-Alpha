/**
 * 运行配置状态（Zustand）——当前设备 devId（用于 rgv/{devId}/{topic}）+ 已知设备列表。
 */
import { create } from 'zustand';
import { APP_CONFIG } from '../config';
import { readString, writeString } from '../auth/storage';

interface ConfigStore {
  devId: string;
  knownDevices: string[];
  setDevId: (id: string) => void;
  addDevice: (id: string) => void;
}

function loadDevId(): string {
  return readString(APP_CONFIG.storageKeys.devId) ?? APP_CONFIG.defaultDevId;
}

export const useConfigStore = create<ConfigStore>((set) => ({
  devId: loadDevId(),
  knownDevices: [APP_CONFIG.defaultDevId],
  setDevId: (id) => {
    writeString(APP_CONFIG.storageKeys.devId, id);
    set((st) =>
      st.knownDevices.includes(id) ? { devId: id } : { devId: id, knownDevices: [...st.knownDevices, id] },
    );
  },
  addDevice: (id) =>
    set((st) =>
      st.knownDevices.includes(id) ? {} : { knownDevices: [...st.knownDevices, id] },
    ),
}));
