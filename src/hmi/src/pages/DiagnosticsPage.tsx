import { useTelemetryStore } from '../store/telemetryStore';
import { useLogStore } from '../store/logStore';
import { FaultBadge } from '../components/FaultBadge';
import { fmt } from '../utils';

export function DiagnosticsPage() {
  const latest = useTelemetryStore((s) => s.latest);
  const diag = useLogStore((s) => s.diag);
  const isSafe = latest.is_safe === true || latest.is_safe === 1;

  return (
    <div>
      <div className="section-title">诊断与告警（四级容错 · ADR-006）</div>

      <div className="card">
        <h3>实时容错状态</h3>
        <div className="row">
          <FaultBadge level={typeof latest.fault_level === 'number' ? latest.fault_level : undefined} />
          {isSafe ? (
            <span className="badge ok">安全回路正常</span>
          ) : (
            <span className="badge err">安全回路异常</span>
          )}
          <span className="badge">fault_code={fmt(latest.fault_code)}</span>
          <span className="badge">laser_status={fmt(latest.laser_status)}</span>
          <span className="badge">photoelectric={fmt(latest.photoelectric_state)}</span>
          <span className="badge">motor_temp={fmt(latest.motor_temp_c)}°C</span>
          <span className="badge">motor_current={fmt(latest.motor_current_a)}A</span>
        </div>
      </div>

      <div className="card">
        <h3>诊断日志 diag/log</h3>
        {diag.length === 0 ? (
          <div className="muted">暂无诊断日志</div>
        ) : (
          <div className="loglist">
            {diag.map((e) => (
              <div className="logitem" key={e.id}>
                <span className="t">{new Date(e.ts).toLocaleTimeString()} </span>
                <span>{JSON.stringify(e.payload)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
