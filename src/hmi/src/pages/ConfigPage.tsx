import { useState } from 'react';
import { commService } from '../comm/CommService';
import { useAuth } from '../auth/AuthContext';
import { ConfirmDialog } from '../components/ConfirmDialog';

export function ConfigPage() {
  const can = useAuth().can;
  const [paramsJson, setParamsJson] = useState('{\n  "speed_limit": 1200,\n  "photoelectric_threshold": 80\n}');
  const [paramMsg, setParamMsg] = useState('');
  const [smdlVersion, setSmdlVersion] = useState('');
  const [smdlRevision, setSmdlRevision] = useState('1');
  const [smdlBody, setSmdlBody] = useState('{}');
  const [smdlMsg, setSmdlMsg] = useState('');
  const [confirmReset, setConfirmReset] = useState(false);

  const submitParam = () => {
    if (!can('config.param')) {
      setParamMsg('无权限：需 engineer 及以上');
      return;
    }
    try {
      const params = JSON.parse(paramsJson) as Record<string, number>;
      const ok = commService.setParam(params);
      setParamMsg(ok ? '已发布 param/set（QoS1）' : '离线缓存：连接后自动冲刷');
    } catch {
      setParamMsg('JSON 解析失败');
    }
  };

  const submitSmdl = () => {
    if (!can('config.smdl')) {
      setSmdlMsg('无权限：需 engineer 及以上');
      return;
    }
    try {
      const body = JSON.parse(smdlBody);
      const ok = commService.pushSmdl({
        smdl_version: smdlVersion || undefined,
        smdl_revision: Number(smdlRevision) || undefined,
        body,
      });
      setSmdlMsg(ok ? '已发布 config/smdl' : '离线缓存：连接后自动冲刷');
    } catch {
      setSmdlMsg('JSON 解析失败');
    }
  };

  const doReset = () => {
    const ok = commService.factoryReset();
    setConfirmReset(false);
    setParamMsg(ok ? '已发布恢复出厂 factory_reset_req=1' : '离线缓存：连接后自动冲刷');
  };

  return (
    <div>
      <div className="section-title">参数配置（param/set · config/smdl · 恢复出厂）</div>

      <div className="card">
        <h3>参数热调 param/set</h3>
        <label className="field">
          <span>参数 JSON（param_revision 由 CFW 自增，ADR-007）</span>
          <textarea rows={5} value={paramsJson} onChange={(e) => setParamsJson(e.target.value)} />
        </label>
        <div className="row">
          <button className="primary" onClick={submitParam} disabled={!can('config.param')}>
            提交 param/set
          </button>
          {!can('config.param') && <span className="badge warn">需 engineer</span>}
        </div>
        {paramMsg && <div className="muted" style={{ marginTop: 8 }}>{paramMsg}</div>}
      </div>

      <div className="card">
        <h3>SMDL 下发 config/smdl</h3>
        <div className="grid">
          <label className="field">
            <span>smdl_version</span>
            <input value={smdlVersion} onChange={(e) => setSmdlVersion(e.target.value)} />
          </label>
          <label className="field">
            <span>smdl_revision</span>
            <input
              type="number"
              value={smdlRevision}
              onChange={(e) => setSmdlRevision(e.target.value)}
            />
          </label>
        </div>
        <label className="field">
          <span>SMDL 主体 JSON</span>
          <textarea rows={4} value={smdlBody} onChange={(e) => setSmdlBody(e.target.value)} />
        </label>
        <div className="row">
          <button className="primary" onClick={submitSmdl} disabled={!can('config.smdl')}>
            下发 config/smdl
          </button>
          {!can('config.smdl') && <span className="badge warn">需 engineer</span>}
        </div>
        {smdlMsg && <div className="muted" style={{ marginTop: 8 }}>{smdlMsg}</div>}
      </div>

      <div className="card">
        <h3>恢复出厂（factory_reset，ADR-007）</h3>
        <p className="muted">复位参数层并自增 param_version；不影响固件/SMDL。仅管理员可执行。</p>
        <div className="row">
          <button className="danger" onClick={() => setConfirmReset(true)} disabled={!can('system.factory_reset')}>
            恢复出厂
          </button>
          {!can('system.factory_reset') && <span className="badge err">需 admin</span>}
        </div>
      </div>

      <ConfirmDialog
        open={confirmReset}
        title="确认恢复出厂？"
        message="将复位参数层并自增 param_version，此操作不可撤销。"
        confirmText="确认恢复"
        danger
        onConfirm={doReset}
        onCancel={() => setConfirmReset(false)}
      />
    </div>
  );
}
