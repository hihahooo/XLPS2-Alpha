/**
 * 任务下发 Modbus 语义映射（ADR-004）
 *
 * - 功能码 FC=0x10（写多个寄存器），保持寄存器基址 0x2000。
 * - 负载布局（5 个保持寄存器 / 10 字节）：
 *     reg0 task_id          (uint16)
 *     reg1 task_type        (uint16)  1=取货 2=放货（业务语义，CFW 解释）
 *     reg2 task_target_pos_mm 高16位 (uint16)
 *     reg3 task_target_pos_mm 低16位 (uint16, int32 小端拆分)
 *     reg4 task_axis        (uint16)  1=D_00 行走伺服 / 2=D_01 顶升伺服
 * - 帧尾 CRC16-MODBUS（低字节在前）。
 *
 * 与 CANopen 内部伺服控制解耦——Modbus 仅下发任务语义，伺服执行走内部 CAN（CiA402）。
 */
export interface TaskCommand {
  task_id: number; // uint16
  task_type: number; // uint16
  task_target_pos_mm: number; // int32（相对真0点距离 mm）
  task_axis: 1 | 2; // 1=D_00 行走, 2=D_01 顶升
}

export interface ModbusResult {
  ok: boolean;
  echo?: Uint8Array;
  error?: string;
}

/** Modbus 传输通道抽象（本地 RS485 / Web Serial / Capacitor 串口插件 均可适配） */
export interface ModbusTransport {
  send(frame: Uint8Array): Promise<ModbusResult>;
}

function writeU16(buf: Uint8Array, off: number, val: number): void {
  buf[off] = (val >> 8) & 0xff;
  buf[off + 1] = val & 0xff;
}

/** CRC16-MODBUS（多项式 0x8005，初始 0xFFFF，结果低字节在前） */
export function crc16Modbus(bytes: Uint8Array): number {
  let crc = 0xffff;
  for (let i = 0; i < bytes.length; i++) {
    crc ^= bytes[i];
    for (let b = 0; b < 8; b++) {
      if (crc & 1) crc = (crc >> 1) ^ 0xa001;
      else crc >>= 1;
    }
  }
  return crc & 0xffff;
}

/** 构建 Modbus RTU 写多寄存器帧（FC=0x10，基址 0x2000） */
export function buildModbusFrame(slave: number, task: TaskCommand): Uint8Array {
  const base = 0x2000;
  const qty = 5;
  const regs = new Uint8Array(qty * 2);
  writeU16(regs, 0, task.task_id & 0xffff);
  writeU16(regs, 2, task.task_type & 0xffff);
  const t = task.task_target_pos_mm | 0; // int32
  writeU16(regs, 4, (t >>> 16) & 0xffff);
  writeU16(regs, 6, t & 0xffff);
  writeU16(regs, 8, task.task_axis & 0xffff);

  const frame = new Uint8Array(1 + 1 + 2 + 2 + 1 + regs.length + 2);
  let o = 0;
  frame[o++] = slave & 0xff;
  frame[o++] = 0x10; // FC
  frame[o++] = (base >> 8) & 0xff;
  frame[o++] = base & 0xff;
  frame[o++] = (qty >> 8) & 0xff;
  frame[o++] = qty & 0xff;
  frame[o++] = regs.length; // byte count
  frame.set(regs, o);
  o += regs.length;
  const crc = crc16Modbus(frame.subarray(0, o));
  frame[o++] = crc & 0xff;
  frame[o++] = (crc >> 8) & 0xff;
  return frame;
}

/** 演示用传输：直接回 ACK（不触达真实串口）。生产替换为 SerialTransport。 */
export class MockModbusTransport implements ModbusTransport {
  async send(frame: Uint8Array): Promise<ModbusResult> {
    const ack = new Uint8Array([frame[0], 0x10, 0x00]); // slave, FC, 0x00=成功
    return { ok: true, echo: ack };
  }
}

/**
 * Web Serial 传输（浏览器/部分安卓 Chrome 支持；Capacitor 需串口插件时替换为对应实现）。
 * 此处仅给出集成骨架，无串口环境时返回错误，便于优雅降级到 MQTT 通道。
 */
// 最小 Web Serial 类型（标准 DOM lib 未内置 SerialPort 全局类型）
interface WebSerialPort {
  open(options: { baudRate: number }): Promise<void>;
  close(): Promise<void>;
  writable: {
    getWriter(): { write(data: Uint8Array): Promise<void>; releaseLock(): void };
  };
}

export class WebSerialModbusTransport implements ModbusTransport {
  constructor(private port?: WebSerialPort) {}
  async send(frame: Uint8Array): Promise<ModbusResult> {
    const nav = navigator as unknown as {
      serial?: { requestPort?: () => Promise<WebSerialPort> };
    };
    const port = this.port ?? (await nav.serial?.requestPort?.());
    if (!port) return { ok: false, error: 'Web Serial 不可用（需浏览器/插件支持）' };
    try {
      await port.open({ baudRate: 19200 });
      const writer = port.writable.getWriter();
      await writer.write(frame);
      writer.releaseLock();
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    } finally {
      await port.close().catch(() => undefined);
    }
  }
}
