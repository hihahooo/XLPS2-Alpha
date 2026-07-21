/**
 * 10 个 MQTT 主题（SSOT 镜像：config/mqtt_topics.json）
 *
 * 主题模式：rgv/{devId}/{topic}（devId 由路径承载，不进入 payload）。
 * 方向语义（ADR-002）：cloud=云端/operator，device=控制器，hmi=安卓 App。
 * HMI 作为现场 operator 控制台，可发布 downlink（operator→device）与 hmi→cloud 主题。
 */
import mqttTopicsJson from '../../../../config/mqtt_topics.json';

export interface TopicMeta {
  topic: string;
  direction: string;
  qos: number;
  payload: string;
}

interface RawTopics {
  schema_version: string;
  source_of_truth: string;
  topic_pattern: string;
  note: string;
  topics: TopicMeta[];
}

export const MQTT_TOPICS_DOC = mqttTopicsJson as unknown as RawTopics;
export const TOPIC_PATTERN = MQTT_TOPICS_DOC.topic_pattern; // "rgv/{devId}/{topic}"
export const TOPIC_META_LIST: TopicMeta[] = MQTT_TOPICS_DOC.topics;
export const TOPIC_COUNT = TOPIC_META_LIST.length;

/** 10 个主题名（字面量联合） */
export type TopicName =
  | 'ota/cmd'
  | 'ota/data'
  | 'ota/progress'
  | 'ota/result'
  | 'param/set'
  | 'telemetry'
  | 'config/smdl'
  | 'interference/sync'
  | 'audit/log'
  | 'diag/log';

const META_BY_TOPIC: Record<string, TopicMeta> = {};
for (const t of TOPIC_META_LIST) META_BY_TOPIC[t.topic] = t;

export function getTopicMeta(name: string): TopicMeta | undefined {
  return META_BY_TOPIC[name];
}

/** 拼接完整主题路径：rgv/{devId}/{topic} */
export function topicFor(devId: string, name: TopicName | string): string {
  return `rgv/${devId}/${name}`;
}

/**
 * HMI 订阅（uplink / 双向中来自设备侧）：
 *  telemetry、ota/progress、ota/result、diag/log、interference/sync
 */
export const HMI_SUBSCRIBE: TopicName[] = [
  'telemetry',
  'ota/progress',
  'ota/result',
  'diag/log',
  'interference/sync',
];

/**
 * HMI 发布（downlink operator→device / hmi→cloud / 双向中来自 HMI 侧）：
 *  param/set、config/smdl、ota/cmd、ota/data、audit/log、interference/sync
 */
export const HMI_PUBLISH: TopicName[] = [
  'param/set',
  'config/smdl',
  'ota/cmd',
  'ota/data',
  'audit/log',
  'interference/sync',
];

/** OTA 触发相关主题（RBAC: admin） */
export const OTA_TOPICS: TopicName[] = ['ota/cmd', 'ota/data', 'ota/progress', 'ota/result'];
/** 参数/SMDL 配置相关主题（RBAC: engineer+） */
export const CONFIG_TOPICS: TopicName[] = ['param/set', 'config/smdl'];
