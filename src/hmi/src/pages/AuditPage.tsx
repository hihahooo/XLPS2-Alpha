import { useLogStore } from '../store/logStore';
import { fmt } from '../utils';

export function AuditPage() {
  const audit = useLogStore((s) => s.audit);

  return (
    <div>
      <div className="section-title">审计日志（audit/log · HMI 上报）</div>
      <div className="card">
        {audit.length === 0 ? (
          <div className="muted">暂无审计记录（操作将经 audit/log 上报）</div>
        ) : (
          <div className="loglist">
            {audit.map((e) => {
              const p = e.payload as Record<string, unknown>;
              return (
                <div className="logitem" key={e.id}>
                  <span className="t">{new Date(e.ts).toLocaleTimeString()} </span>
                  <span className="badge">{fmt(p.action)}</span>{' '}
                  <span className="muted">by {fmt(p.operator)}</span>{' '}
                  <span>{JSON.stringify(p.detail)}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
