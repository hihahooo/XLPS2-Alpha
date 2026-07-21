/** 数值/文本格式化：未定义显示占位符；浮点保留 2 位。 */
export function fmt(v: unknown): string {
  if (v === undefined || v === null || v === '') return '—';
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(2);
  return String(v);
}

export function toNumber(v: string, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}
