import { useConnectionStore } from '../store/connectionStore';
import type { ConnStatus } from '../mqtt/MqttClient';

const LABEL: Record<ConnStatus, string> = {
  disconnected: '已断开',
  connecting: '连接中',
  connected: '已连接',
  reconnecting: '重连中',
  error: '错误',
};

export function ConnBadge() {
  const status = useConnectionStore((s) => s.status);
  const attempt = useConnectionStore((s) => s.attempt);
  const dot = status === 'connected' ? 'ok' : status === 'error' ? 'err' : 'warn';
  return (
    <span className="badge">
      <span className={`dot ${dot}`} />
      {LABEL[status]}
      {attempt > 0 ? ` (${attempt})` : ''}
    </span>
  );
}
