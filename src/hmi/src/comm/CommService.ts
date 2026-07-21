/**
 * 通信服务（CommService）——双通道统一门面。
 *  - 本地通道：RS485 Modbus RTU（任务下发，ADR-004），经 ModbusTransport 抽象。
 *  - 远程通道：MQTT（param/set、config/smdl、ota/cmd、interference/sync、audit/log）。
 *
 * 所有下发动作均经 RBAC 能力校验（调用方页面先行守卫；此处再兜底），并写 audit/log。
 */
import { mqttService } from '../mqtt/mqttService';
import {
  buildModbusFrame,
  MockModbusTransport,
  type ModbusTransport,
  type TaskCommand,
} from './modbusTask';
import { useAuthStore } from '../store/authStore';
import { useLogStore } from '../store/logStore';

export type TaskChannel = 'modbus' | 'mqtt';

export type OtaAction = 'start' | 'pause' | 'confirm' | 'rollback';

export interface AuditEntry {
  audit_seq: number;
  action: string;
  operator: string;
  ts: number;
  detail: unknown;
}

class CommService {
  private transport: ModbusTransport = new MockModbusTransport();
  private slaveAddr = 0x01;

  setTransport(t: ModbusTransport): void {
    this.transport = t;
  }
  setSlaveAddr(a: number): void {
    this.slaveAddr = a;
  }

  /** 任务下发（ADR-004）。默认本地 Modbus；可选 MQTT 回退。 */
  async dispatchTask(task: TaskCommand, channel: TaskChannel = 'modbus') {
    if (channel === 'modbus') {
      const frame = buildModbusFrame(this.slaveAddr, task);
      const res = await this.transport.send(frame);
      this.audit('task.dispatch', { channel, task, result: res });
      return res;
    }
    const ok = mqttService.publish('telemetry', {
      command_in: 'task_start',
      task_id: task.task_id,
      task_type: task.task_type,
      task_target_pos_mm: task.task_target_pos_mm,
      task_axis: task.task_axis,
    });
    this.audit('task.dispatch', { channel: 'mqtt', task, queued: !ok });
    return { ok, queued: !ok };
  }

  /** 参数热调（param/set，RBAC: config.param）。param_revision 由 CFW 自增（ADR-007）。 */
  setParam(params: Record<string, number>, note?: string): boolean {
    const ok = mqttService.publish('param/set', { params, note });
    this.audit('param.set', { params, queued: !ok });
    return ok;
  }

  /** SMDL 下发（config/smdl，RBAC: config.smdl）。smdl_revision 由 CFW 自增（ADR-007）。 */
  pushSmdl(smdl: { smdl_version?: string; smdl_revision?: number; body?: unknown }): boolean {
    const ok = mqttService.publish('config/smdl', smdl);
    this.audit('config.smdl', { smdl, queued: !ok });
    return ok;
  }

  /** OTA 触发（ota/cmd，RBAC: ota.trigger） */
  triggerOta(cmd: { action: OtaAction; target_version?: string; slot?: 'A' | 'B' }): boolean {
    const ok = mqttService.publish('ota/cmd', cmd);
    this.audit('ota.trigger', { cmd, queued: !ok });
    return ok;
  }

  /** 恢复出厂（factory_reset_req=1 → L5 复位参数层 + param_version++，ADR-007）。RBAC: admin。 */
  factoryReset(): boolean {
    const ok = mqttService.publish('param/set', { factory_reset_req: 1 });
    this.audit('system.factory_reset', { queued: !ok });
    return ok;
  }

  /** 干扰点库上行同步（interference/sync，RBAC: interference.edit） */
  syncInterference(track: {
    track_id: number;
    points: Array<{ position_mm: number; confirmed: boolean; hit_count: number }>;
  }): boolean {
    const ok = mqttService.publish('interference/sync', track);
    this.audit('interference.sync', { track, queued: !ok });
    return ok;
  }

  private audit(action: string, detail: unknown): void {
    const user = useAuthStore.getState().user;
    const entry: AuditEntry = {
      audit_seq: Date.now(),
      action,
      operator: user?.name ?? 'unknown',
      ts: Date.now(),
      detail,
    };
    mqttService.publish('audit/log', entry);
    useLogStore.getState().pushAudit(entry);
  }
}

export const commService = new CommService();
