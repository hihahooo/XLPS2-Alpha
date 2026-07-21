/**
 * 33 字段统一数据字典（SSOT 镜像：config/data_dictionary.json）
 *
 * 直接引用仓库 SSOT 文件，保证 HMI 与全局契约逐字一致。
 * 若路径解析失败（独立构建），请确认仓库 output/config/data_dictionary.json 存在。
 */
import dataDictionaryJson from '../../../../config/data_dictionary.json';
import type { FieldName } from './types';

export interface FieldMeta {
  name: string;
  type: string;
  unit: string;
  source: string;
  topic: string;
  desc: string;
  adr?: string;
}

interface RawDictionary {
  schema_version: string;
  source_of_truth: string;
  note: string;
  fields: FieldMeta[];
}

export const DATA_DICTIONARY = dataDictionaryJson as unknown as RawDictionary;
export const FIELD_META_LIST: FieldMeta[] = DATA_DICTIONARY.fields;
export const FIELD_NAMES = FIELD_META_LIST.map((f) => f.name) as FieldName[];
export const FIELD_COUNT = FIELD_META_LIST.length;

const META_BY_NAME: Record<string, FieldMeta> = {};
for (const f of FIELD_META_LIST) META_BY_NAME[f.name] = f;

export function getFieldMeta(name: string): FieldMeta | undefined {
  return META_BY_NAME[name];
}

/** 按 topic 归类字段（用于页面布局分组） */
export function fieldsByTopic(topic: string): FieldMeta[] {
  return FIELD_META_LIST.filter((f) => f.topic === topic);
}
