import { FIELD_META_LIST } from '../contract/dataDictionary';
import type { Telemetry } from '../contract/types';

/** 33 字段表格（可按 topic 过滤）。值与 SSOT 数据字典逐字段对应。 */
export function FieldTable({ telemetry, filterTopic }: { telemetry: Telemetry; filterTopic?: string }) {
  const rows = filterTopic
    ? FIELD_META_LIST.filter((f) => f.topic === filterTopic)
    : FIELD_META_LIST;
  return (
    <table className="tbl">
      <thead>
        <tr>
          <th>字段</th>
          <th>值</th>
          <th>单位</th>
          <th>类型</th>
          <th>来源</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((f) => {
          const v = telemetry[f.name as keyof Telemetry];
          return (
            <tr key={f.name}>
              <td>{f.name}</td>
              <td>{v === undefined || v === null ? '—' : String(v)}</td>
              <td className="muted">{f.unit || '—'}</td>
              <td className="muted">{f.type}</td>
              <td className="muted">{f.source}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
