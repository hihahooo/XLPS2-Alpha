import type { FaultLevel } from '../contract/types';

// 四级容错（ADR-006）：级别编号 ≠ 执行顺序
// 一级 CHECK_DIST / 二级 NUDGE_RETRY / 四级 CROSS_VERIFY / 三级 SLOW_STOP·ESTOP
const MAP: Record<number, { cls: string; label: string }> = {
  1: { cls: 'ok', label: '一级 软滤波(CHECK_DIST)' },
  2: { cls: 'warn', label: '二级 微动重试(NUDGE_RETRY)' },
  3: { cls: 'warn', label: '三级 分级停车/急停(SLOW_STOP·ESTOP)' },
  4: { cls: 'err', label: '四级 交叉验证(CROSS_VERIFY)' },
};

export function FaultBadge({ level }: { level: number | undefined }) {
  if (level === undefined || level === null) return <span className="badge">fault_level —</span>;
  const m = MAP[level] ?? { cls: '', label: `级别 ${level}` };
  return (
    <span className={`badge ${m.cls}`}>
      fault_level={level} {m.label}
    </span>
  );
}

export type { FaultLevel };
