/**
 * XLPS2-Alpha · 跨模块契约层（SSOT 镜像）
 *
 * 本文件为 HMI 与 SSOT 唯一事实源对齐的核心：
 *  - 33 字段遥测类型（详见 dataDictionary.ts，镜像 config/data_dictionary.json）
 *  - 10 个 MQTT 主题（详见 topics.ts，镜像 config/mqtt_topics.json）
 *  - current_state 层级解码（ADR-003）：(region<<14)|(top_state<<8)|sub_state；0xFFFF=未初始化
 *
 * 解码位运算必须与 OTA/云端的 schema.py 逐字节一致（见 ADR-003）。
 */

// ============================================================================
// 1. 字段名（33，与 data_dictionary.json 完全一致）
// ============================================================================
export type FieldName =
  | 'current_state'
  | 'position_mm'
  | 'speed_mm_s'
  | 'battery_soc'
  | 'track_id'
  | 'task_status'
  | 'task_progress_pct'
  | 'fault_code'
  | 'fault_level'
  | 'motor_current_a'
  | 'motor_temp_c'
  | 'encoder_position'
  | 'laser_status'
  | 'photoelectric_state'
  | 'ota_active_slot'
  | 'ota_state'
  | 'ota_progress_pct'
  | 'ota_target_version'
  | 'ota_result'
  | 'fw_version'
  | 'smdl_version'
  | 'param_revision'
  | 'smdl_revision'
  | 'interference_count'
  | 'diag_code'
  | 'audit_seq'
  | 'top_state'
  | 'sub_state'
  | 'region'
  | 'is_safe'
  | 'command_in'
  | 'heartbeat_ts'
  | 'uptime_s';

export type Scalar = number | string | boolean;
/** 遥测快照：33 字段最新值（字段可缺省/未到） */
export type Telemetry = Partial<Record<FieldName, Scalar>>;

// ============================================================================
// 2. 枚举值域（展示/校验用；取值与 SSOT 描述一致）
// ============================================================================
export type TaskStatus = 'idle' | 'running' | 'paused' | 'done' | 'failed' | 'canceled';
export type LaserStatus = 'ok' | 'triggered' | 'error';
export type PhotoelectricState = 'clear' | 'blocked' | 'error';
export type OtaSlot = 'A' | 'B';
export type OtaState = 'idle' | 'downloading' | 'flashing' | 'verifying' | 'active' | 'rollback';
export type OtaResult = 'ok' | 'fail' | 'rollback';
export type CommandIn =
  | 'none'
  | 'move'
  | 'lift'
  | 'task_start'
  | 'task_pause'
  | 'task_cancel'
  | 'factory_reset'
  | 'param_set'
  | 'ota_start';

export type FaultLevel = 1 | 2 | 3 | 4;

// ============================================================================
// 3. current_state 层级编码（ADR-003）
// ============================================================================
export const UNINIT_STATE = 0xffff; // 未初始化哨兵值

export type RegionId = 0 | 1 | 2;

/** 3 个并行正交区域（最高优先级仲裁依据） */
export const REGION = {
  0: { id: 0 as RegionId, name: 'MAIN', label: '主业务区' },
  1: { id: 1 as RegionId, name: 'POWER', label: '能源管理区' },
  2: { id: 2 as RegionId, name: 'SAFETY', label: '安全监控区' },
} as const;

/** 顶层状态（top_state）编码表：按区域分桶，可逆向解析（ADR-003） */
export const TOP_STATE_TABLE: Record<RegionId, Record<number, { name: string; label: string }>> = {
  // 区域0 主业务区
  0: {
    1: { name: 'BOOTING', label: '启动中' },
    2: { name: 'IDLE', label: '空闲' },
    3: { name: 'TASK_RUNNING', label: '任务运行' },
    4: { name: 'FIND_ZERO', label: '找真0点' },
    5: { name: 'TRACK_IDENTIFY', label: '轨道识别' },
    6: { name: 'DISPATCHING', label: '调度下发' },
    7: { name: 'TRAVELING', label: '行走' },
    8: { name: 'LOADING', label: '装载(伸叉/顶升/缩叉)' },
    9: { name: 'UNLOADING', label: '卸载' },
    10: { name: 'RETURNING', label: '返航' },
  },
  // 区域1 能源管理区
  1: {
    1: { name: 'POWER_NORMAL', label: '电量正常' },
    2: { name: 'LOW_BATTERY', label: '低电量' },
    3: { name: 'CHARGING', label: '充电中' },
  },
  // 区域2 安全监控区（最高优先级）
  2: {
    1: { name: 'SAFE_OK', label: '安全正常' },
    2: { name: 'WARNING', label: '安全告警' },
    3: { name: 'ESTOP', label: '急停(全局捕获)' },
  },
};

/** 子状态（sub_state）编码表：0=无 */
export const SUB_STATE_TABLE: Record<number, { name: string; label: string }> = {
  0: { name: 'NONE', label: '—' },
  1: { name: 'IDENTIFIED', label: '已识别(有码)' },
  2: { name: 'ANONYMOUS', label: '匿名(无码)' },
  3: { name: 'ACCEL', label: '加速' },
  4: { name: 'CRUISE', label: '巡航' },
  5: { name: 'CHECK_DIST', label: '距离校验' },
  6: { name: 'DECEL', label: '减速' },
  7: { name: 'POSITIONING', label: '定位' },
  8: { name: 'NUDGE_RETRY', label: '微动重试' },
  9: { name: 'CROSS_VERIFY', label: '交叉验证' },
  10: { name: 'FORK_OUT', label: '伸叉' },
  11: { name: 'LIFT', label: '顶升' },
  12: { name: 'FORK_IN', label: '缩叉' },
};

/** ESTOP 顶层状态码（安全区 region=2, top=3） */
export const ESTOP_TOP = 3;

export interface DecodedState {
  raw: number;
  uninit: boolean;
  region: RegionId;
  regionName: string;
  regionLabel: string;
  topState: number;
  topStateName: string;
  topStateLabel: string;
  subState: number;
  subStateName: string;
  subStateLabel: string;
  /** 层级路径，例：主业务区.行走.距离校验 */
  path: string;
  /** region=2 && top=ESTOP → 全局急停 */
  isEStop: boolean;
  isWarning: boolean;
}

/**
 * 解码 current_state（ADR-003）。
 * current_state = (region<<14) | (top_state<<8) | sub_state ；0xFFFF=未初始化。
 *
 * ⚠️ SSOT 位域注意：region 占 bits 14-15，恰为 top_state 字节（bits 8-15）的高 2 位，
 * 因此 top_state 实际可用 6 位（bits 8-13，掩码 0x3F）；编码时 top_state 须 & 0x3F，
 * 否则 region≠0 时会与 top_state 高位重叠、无法正确还原。所有命名状态编码均 ≤ 0x3F。
 */
export function decodeCurrentState(raw: number): DecodedState {
  const r = raw & 0xffff;
  if (r === UNINIT_STATE) {
    return {
      raw,
      uninit: true,
      region: 0,
      regionName: REGION[0].name,
      regionLabel: REGION[0].label,
      topState: 0,
      topStateName: 'UNINIT',
      topStateLabel: '未初始化',
      subState: 0,
      subStateName: 'NONE',
      subStateLabel: '—',
      path: `${REGION[0].label}.未初始化`,
      isEStop: false,
      isWarning: false,
    };
  }
  const region = ((r >> 14) & 0x03) as RegionId;
  const topState = (r >> 8) & 0x3f;
  const subState = r & 0xff;

  const rg = REGION[region];
  const top = TOP_STATE_TABLE[region]?.[topState] ?? {
    name: `TOP_${topState}`,
    label: `顶层#${topState}`,
  };
  const sub = SUB_STATE_TABLE[subState] ?? {
    name: `SUB_${subState}`,
    label: `子态#${subState}`,
  };

  const path = `${rg.label}.${top.label}` + (subState !== 0 ? `.${sub.label}` : '');
  const isEStop = region === 2 && topState === ESTOP_TOP;
  const isWarning = region === 2 && topState === 2;

  return {
    raw,
    uninit: false,
    region,
    regionName: rg.name,
    regionLabel: rg.label,
    topState,
    topStateName: top.name,
    topStateLabel: top.label,
    subState,
    subStateName: sub.name,
    subStateLabel: sub.label,
    path,
    isEStop,
    isWarning,
  };
}

/** 编码 current_state（与 decodeCurrentState 互逆；top_state 掩码 0x3F，见上方说明） */
export function encodeCurrentState(region: RegionId, topState: number, subState = 0): number {
  return ((region & 0x03) << 14) | ((topState & 0x3f) << 8) | (subState & 0xff);
}
