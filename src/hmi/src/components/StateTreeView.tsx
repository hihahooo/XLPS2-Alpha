import { decodeCurrentState, REGION, UNINIT_STATE } from '../contract/types';

/** 三正交区域可视化（ADR-003）：高亮当前区域，展示层级路径；安全区红框，ESTOP 全局提示。 */
export function StateTreeView({ raw }: { raw: number | undefined }) {
  const value = typeof raw === 'number' ? raw : UNINIT_STATE;
  const decoded = decodeCurrentState(value);
  return (
    <div>
      {([0, 1, 2] as const).map((rid) => {
        const active = decoded.region === rid;
        const rg = REGION[rid];
        return (
          <div
            key={rid}
            className={`region ${rid === 2 ? 'safety' : ''}`}
            style={active ? { borderColor: 'var(--accent)', opacity: 1 } : { opacity: 0.55 }}
          >
            <div className="rname">
              {rg.label} {active ? '●' : ''}
            </div>
            {active && <div className="path">{decoded.path}</div>}
          </div>
        );
      })}
      {decoded.isEStop && <div className="badge err">全局急停 ESTOP（region=2）</div>}
      {decoded.uninit && <div className="badge warn">未初始化 0xFFFF</div>}
    </div>
  );
}
