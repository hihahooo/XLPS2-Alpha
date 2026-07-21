import { useState } from 'react';
import { commService, type OtaAction } from '../comm/CommService';
import { useTelemetryStore } from '../store/telemetryStore';
import { useAuth } from '../auth/AuthContext';
import { fmt } from '../utils';

function Kpi({ label, value, unit }: { label: string; value: unknown; unit?: string }) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className="value">
        {fmt(value)}
        {unit ? <span className="unit">{unit}</span> : null}
      </div>
    </div>
  );
}

export function OtaPage() {
  const can = useAuth().can;
  const latest = useTelemetryStore((s) => s.latest);
  const [action, setAction] = useState<OtaAction>('start');
  const [targetVersion, setTargetVersion] = useState('');
  const [slot, setSlot] = useState<'A' | 'B'>('B');
  const [msg, setMsg] = useState('');

  const trigger = () => {
    if (!can('ota.trigger')) {
      setMsg('无权限：需 admin');
      return;
    }
    const ok = commService.triggerOta({
      action,
      target_version: targetVersion || undefined,
      slot,
    });
    setMsg(ok ? `已发布 ota/cmd action=${action}` : '离线缓存：连接后自动冲刷');
  };

  return (
    <div>
      <div className="section-title">OTA 升级（ota/cmd · ota/progress · ota/result · ADR-005）</div>

      <div className="grid" style={{ marginBottom: 14 }}>
        <Kpi label="ota_state" value={latest.ota_state} />
        <Kpi label="ota_progress_pct" value={latest.ota_progress_pct} unit="%" />
        <Kpi label="ota_active_slot" value={latest.ota_active_slot} />
        <Kpi label="ota_target_version" value={latest.ota_target_version} />
        <Kpi label="ota_result" value={latest.ota_result} />
      </div>

      <div className="card">
        <h3>触发 OTA（仅管理员）</h3>
        <div className="grid">
          <label className="field">
            <span>action</span>
            <select value={action} onChange={(e) => setAction(e.target.value as OtaAction)}>
              <option value="start">start（下发到非活跃分区）</option>
              <option value="pause">pause</option>
              <option value="confirm">confirm（健康确认）</option>
              <option value="rollback">rollback（回滚）</option>
            </select>
          </label>
          <label className="field">
            <span>target_version（须严格大于当前，版本单调）</span>
            <input value={targetVersion} onChange={(e) => setTargetVersion(e.target.value)} />
          </label>
          <label className="field">
            <span>slot</span>
            <select value={slot} onChange={(e) => setSlot(e.target.value as 'A' | 'B')}>
              <option value="A">A</option>
              <option value="B">B</option>
            </select>
          </label>
        </div>
        <div className="row">
          <button className="primary" onClick={trigger} disabled={!can('ota.trigger')}>
            触发 OTA
          </button>
          {!can('ota.trigger') && <span className="badge err">需 admin</span>}
        </div>
        {msg && <div className="muted" style={{ marginTop: 8 }}>{msg}</div>}
      </div>
    </div>
  );
}
