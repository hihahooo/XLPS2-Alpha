import { useTelemetryStore } from '../store/telemetryStore';
import { StateTreeView } from '../components/StateTreeView';
import { FieldTable } from '../components/FieldTable';
import { FaultBadge } from '../components/FaultBadge';
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

export function DashboardPage() {
  const latest = useTelemetryStore((s) => s.latest);
  const updatedAt = useTelemetryStore((s) => s.updatedAt);
  const raw = typeof latest.current_state === 'number' ? latest.current_state : undefined;
  const isSafe = latest.is_safe === true || latest.is_safe === 1;

  return (
    <div>
      <div className="section-title">实时状态 · current_state（ADR-003）</div>
      <div className="grid" style={{ marginBottom: 14 }}>
        <Kpi label="位置 position_mm" value={latest.position_mm} unit="mm" />
        <Kpi label="速度 speed_mm_s" value={latest.speed_mm_s} unit="mm/s" />
        <Kpi label="电量 battery_soc" value={latest.battery_soc} unit="%" />
        <Kpi label="任务进度 task_progress_pct" value={latest.task_progress_pct} unit="%" />
        <Kpi label="OTA 进度 ota_progress_pct" value={latest.ota_progress_pct} unit="%" />
        <Kpi label="上电 uptime_s" value={latest.uptime_s} unit="s" />
      </div>

      <div className="card">
        <h3>三正交区域状态机</h3>
        <StateTreeView raw={raw} />
        <div className="row" style={{ marginTop: 8 }}>
          {isSafe ? (
            <span className="badge ok">安全回路正常 is_safe=1</span>
          ) : (
            <span className="badge err">安全回路异常 is_safe=0</span>
          )}
          <FaultBadge level={typeof latest.fault_level === 'number' ? latest.fault_level : undefined} />
          {latest.task_status && (
            <span className="badge">task_status={fmt(latest.task_status)}</span>
          )}
          {latest.ota_state && <span className="badge">ota_state={fmt(latest.ota_state)}</span>}
        </div>
      </div>

      <div className="card">
        <h3>33 字段遥测（SSOT · config/data_dictionary.json）</h3>
        <FieldTable telemetry={latest} />
        <div className="muted" style={{ marginTop: 8 }}>
          最后更新：{updatedAt ? new Date(updatedAt).toLocaleTimeString() : '—'}
        </div>
      </div>
    </div>
  );
}
