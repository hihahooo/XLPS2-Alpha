import { describe, it, expect } from 'vitest';
import {
  decodeCurrentState,
  encodeCurrentState,
  UNINIT_STATE,
} from '../src/contract/types';
import { FIELD_NAMES, FIELD_COUNT } from '../src/contract/dataDictionary';
import {
  TOPIC_META_LIST,
  TOPIC_COUNT,
  HMI_SUBSCRIBE,
  HMI_PUBLISH,
  topicFor,
} from '../src/contract/topics';
import { crc16Modbus, buildModbusFrame } from '../src/comm/modbusTask';
// SSOT 单一事实源（仓库 config/）
import dataDict from '../../../config/data_dictionary.json';
import mqttTopics from '../../../config/mqtt_topics.json';

describe('current_state 解码（ADR-003）', () => {
  it('未初始化哨兵 0xFFFF', () => {
    const d = decodeCurrentState(UNINIT_STATE);
    expect(d.uninit).toBe(true);
    expect(d.path).toContain('未初始化');
  });

  it('位运算 (region<<14)|(top_state<<8)|sub_state 可逆', () => {
    const cases: Array<[0 | 1 | 2, number, number]> = [
      [0, 7, 5],
      [1, 3, 0],
      [2, 3, 0],
      [0, 5, 2],
      [0, 8, 11],
    ];
    for (const [r, top, sub] of cases) {
      const enc = encodeCurrentState(r, top, sub);
      const d = decodeCurrentState(enc);
      expect(d.region).toBe(r);
      expect(d.topState).toBe(top);
      expect(d.subState).toBe(sub);
    }
  });

  it('ESTOP 全局捕获（region=2, top=3）', () => {
    const d = decodeCurrentState(encodeCurrentState(2, 3, 0));
    expect(d.isEStop).toBe(true);
  });

  it('层级路径可读（主业务.行走.距离校验）', () => {
    const d = decodeCurrentState(encodeCurrentState(0, 7, 5));
    expect(d.path).toContain('行走');
    expect(d.path).toContain('距离校验');
  });
});

describe('SSOT 契约对齐（33 字段 / 10 主题）', () => {
  it('33 字段与 data_dictionary.json 逐字一致', () => {
    const ssotNames = (dataDict as any).fields.map((f: any) => f.name);
    expect(ssotNames.length).toBe(33);
    expect(FIELD_COUNT).toBe(33);
    expect([...FIELD_NAMES].sort()).toEqual([...ssotNames].sort());
  });

  it('10 主题与 mqtt_topics.json 逐字一致', () => {
    const ssot = (mqttTopics as any).topics.map((t: any) => t.topic);
    expect(ssot.length).toBe(10);
    expect(TOPIC_COUNT).toBe(10);
    expect([...TOPIC_META_LIST.map((t) => t.topic)].sort()).toEqual([...ssot].sort());
  });

  it('主题模式 rgv/{devId}/{topic}', () => {
    expect((mqttTopics as any).topic_pattern).toBe('rgv/{devId}/{topic}');
    expect(topicFor('RGV-1', 'telemetry')).toBe('rgv/RGV-1/telemetry');
  });

  it('HMI 订阅/发布主题均在 10 主题集合内', () => {
    const all = new Set((mqttTopics as any).topics.map((t: any) => t.topic));
    for (const t of [...HMI_SUBSCRIBE, ...HMI_PUBLISH]) expect(all.has(t)).toBe(true);
  });
});

describe('Modbus 任务帧（ADR-004）', () => {
  it('CRC16-MODBUS 为 16 位无符号', () => {
    const crc = crc16Modbus(new Uint8Array([0x01, 0x10, 0x20, 0x00, 0x00, 0x05]));
    expect(crc).toBeGreaterThanOrEqual(0);
    expect(crc).toBeLessThanOrEqual(0xffff);
  });

  it('buildModbusFrame：slave|FC=0x10|addr=0x2000|qty=5|byteCount=10|data|CRC', () => {
    const f = buildModbusFrame(0x01, {
      task_id: 1,
      task_type: 1,
      task_target_pos_mm: 1000,
      task_axis: 1,
    });
    expect(f[0]).toBe(0x01);
    expect(f[1]).toBe(0x10);
    expect((f[2] << 8) | f[3]).toBe(0x2000);
    expect((f[4] << 8) | f[5]).toBe(5);
    expect(f[6]).toBe(10);
    expect(f.length).toBe(1 + 1 + 2 + 2 + 1 + 10 + 2);

    // 帧尾 CRC 自校验
    const crc = crc16Modbus(f.subarray(0, f.length - 2));
    expect((f[f.length - 2] | (f[f.length - 1] << 8)) & 0xffff).toBe(crc);
  });

  it('int32 目标位置高低 16 位拆分正确', () => {
    const f = buildModbusFrame(0x01, {
      task_id: 1,
      task_type: 1,
      task_target_pos_mm: -12345,
      task_axis: 2,
    });
    // 帧布局：7-8 task_id, 9-10 task_type, 11-12 目标位置 hi, 13-14 lo, 15-16 task_axis
    const hi = (f[11] << 8) | f[12];
    const lo = (f[13] << 8) | f[14];
    expect((hi << 16) | lo).toBe(-12345);
  });
});
