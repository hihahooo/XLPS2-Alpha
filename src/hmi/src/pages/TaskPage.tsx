import { useState } from 'react';
import { commService, type TaskChannel } from '../comm/CommService';
import type { TaskCommand } from '../comm/modbusTask';
import { useAuth } from '../auth/AuthContext';
import { toNumber } from '../utils';

export function TaskPage() {
  const can = useAuth().can;
  const [task, setTask] = useState<TaskCommand>({
    task_id: 1,
    task_type: 1,
    task_target_pos_mm: 0,
    task_axis: 1,
  });
  const [channel, setChannel] = useState<TaskChannel>('modbus');
  const [result, setResult] = useState<string>('');

  const dispatch = async () => {
    if (!can('task.dispatch')) {
      setResult('无权限：需 operator 及以上');
      return;
    }
    const res = await commService.dispatchTask(task, channel);
    setResult(JSON.stringify(res));
  };

  return (
    <div>
      <div className="section-title">任务下发（ADR-004 Modbus 语义映射）</div>
      <div className="card">
        <div className="grid">
          <label className="field">
            <span>task_id (uint16)</span>
            <input
              type="number"
              value={task.task_id}
              onChange={(e) => setTask({ ...task, task_id: toNumber(e.target.value, 0) })}
            />
          </label>
          <label className="field">
            <span>task_type (uint16)</span>
            <input
              type="number"
              value={task.task_type}
              onChange={(e) => setTask({ ...task, task_type: toNumber(e.target.value, 0) })}
            />
          </label>
          <label className="field">
            <span>task_target_pos_mm (int32, 相对真0点)</span>
            <input
              type="number"
              value={task.task_target_pos_mm}
              onChange={(e) =>
                setTask({ ...task, task_target_pos_mm: toNumber(e.target.value, 0) })
              }
            />
          </label>
          <label className="field">
            <span>task_axis</span>
            <select
              value={task.task_axis}
              onChange={(e) => setTask({ ...task, task_axis: e.target.value === '2' ? 2 : 1 })}
            >
              <option value={1}>1 = D_00 行走伺服</option>
              <option value={2}>2 = D_01 顶升伺服</option>
            </select>
          </label>
        </div>

        <label className="field">
          <span>下发通道</span>
          <select value={channel} onChange={(e) => setChannel(e.target.value as TaskChannel)}>
            <option value="modbus">本地 RS485 Modbus RTU（FC=0x10, 基址 0x2000）</option>
            <option value="mqtt">远程 MQTT（telemetry/command_in 透传）</option>
          </select>
        </label>

        <div className="row">
          <button className="primary" onClick={dispatch}>
            下发任务
          </button>
          {!can('task.dispatch') && <span className="badge warn">无权限</span>}
        </div>

        {result && (
          <div className="card" style={{ marginTop: 12, background: 'var(--bg-2)' }}>
            <div className="section-title">返回</div>
            <pre className="loglist" style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {result}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
