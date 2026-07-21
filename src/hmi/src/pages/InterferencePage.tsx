import { useState } from 'react';
import { useInterferenceStore } from '../store/interferenceStore';
import { commService } from '../comm/CommService';
import { useAuth } from '../auth/AuthContext';
import { toNumber } from '../utils';

export function InterferencePage() {
  const can = useAuth().can;
  const tracks = useInterferenceStore((s) => s.tracks);
  const upsertPoint = useInterferenceStore((s) => s.upsertPoint);
  const [trackId, setTrackId] = useState('0');
  const [pos, setPos] = useState('');
  const [confirmed, setConfirmed] = useState(true);
  const [hit, setHit] = useState('0');
  const [msg, setMsg] = useState('');

  const add = () => {
    const tid = toNumber(trackId, 0);
    const p = toNumber(pos, 0);
    if (!Number.isFinite(p)) {
      setMsg('position_mm 无效');
      return;
    }
    upsertPoint(tid, { position_mm: p, confirmed, hit_count: toNumber(hit, 0) });
    setMsg('已加入本地编辑（尚未上行）');
  };

  const sync = (tid: number) => {
    if (!can('interference.edit')) {
      setMsg('无权限：需 engineer');
      return;
    }
    const t = tracks[tid];
    if (!t) return;
    const ok = commService.syncInterference(t);
    setMsg(ok ? `已上行同步 track_id=${tid}` : '离线缓存：连接后自动冲刷');
  };

  const trackIds = Object.keys(tracks)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <div>
      <div className="section-title">干扰点库（interference/sync · 以 position_mm 为索引）</div>

      <div className="card">
        <h3>新增/编辑干扰点</h3>
        <div className="grid">
          <label className="field">
            <span>track_id（0=无码匿名）</span>
            <input type="number" value={trackId} onChange={(e) => setTrackId(e.target.value)} />
          </label>
          <label className="field">
            <span>position_mm</span>
            <input type="number" value={pos} onChange={(e) => setPos(e.target.value)} />
          </label>
          <label className="field">
            <span>hit_count</span>
            <input type="number" value={hit} onChange={(e) => setHit(e.target.value)} />
          </label>
          <label className="field">
            <span>confirmed</span>
            <select
              value={confirmed ? '1' : '0'}
              onChange={(e) => setConfirmed(e.target.value === '1')}
            >
              <option value="1">已确认</option>
              <option value="0">未确认</option>
            </select>
          </label>
        </div>
        <button className="primary" onClick={add}>
          加入本地
        </button>
        {msg && <div className="muted" style={{ marginTop: 8 }}>{msg}</div>}
      </div>

      {trackIds.map((tid) => {
        const t = tracks[tid];
        return (
          <div className="card" key={tid}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h3 style={{ margin: 0 }}>track_id = {tid}</h3>
              <button onClick={() => sync(tid)} disabled={!can('interference.edit')}>
                上行同步
              </button>
            </div>
            <table className="tbl">
              <thead>
                <tr>
                  <th>position_mm</th>
                  <th>confirmed</th>
                  <th>hit_count</th>
                </tr>
              </thead>
              <tbody>
                {t.points.map((p) => (
                  <tr key={p.position_mm}>
                    <td>{p.position_mm}</td>
                    <td>{p.confirmed ? '✓' : '—'}</td>
                    <td>{p.hit_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}

      {trackIds.length === 0 && <div className="muted">暂无干扰点（远端同步或本地新增后显示）</div>}
    </div>
  );
}
