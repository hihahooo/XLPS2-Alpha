import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useConnectionStore } from '../store/connectionStore';
import { useConfigStore } from '../store/configStore';
import { mqttService } from '../mqtt/mqttService';
import { ConnBadge } from './ConnBadge';
import { ROLE_LABEL, type Role } from '../auth/rbac';

interface NavItem {
  to: string;
  label: string;
  min: Role;
}

const NAV: NavItem[] = [
  { to: '/dashboard', label: '设备总览', min: 'operator' },
  { to: '/tasks', label: '任务下发', min: 'operator' },
  { to: '/diagnostics', label: '诊断告警', min: 'operator' },
  { to: '/audit', label: '审计日志', min: 'operator' },
  { to: '/interference', label: '干扰点', min: 'engineer' },
  { to: '/config', label: '参数配置', min: 'engineer' },
  { to: '/ota', label: 'OTA 升级', min: 'admin' },
];

export function Layout() {
  const { user, isAtLeast, logout } = useAuth();
  const status = useConnectionStore((s) => s.status);
  const devId = useConfigStore((s) => s.devId);
  const knownDevices = useConfigStore((s) => s.knownDevices);
  const navigate = useNavigate();
  const [devInput, setDevInput] = useState(devId);

  // 登录后自动连接 MQTT（断线重连由 MqttClient 负责）
  useEffect(() => {
    if (user && status === 'disconnected') mqttService.connect();
  }, [user, status]);

  const onLogout = () => {
    mqttService.disconnect();
    logout();
    navigate('/login', { replace: true });
  };

  const applyDevId = () => {
    const v = devInput.trim();
    if (v && v !== devId) mqttService.setDevId(v);
  };

  return (
    <div className="app">
      <div className="topbar">
        <span className="brand">XLPS2 HMI</span>
        <span className="meta">设备</span>
        <input
          style={{ width: 140, height: 36 }}
          value={devInput}
          onChange={(e) => setDevInput(e.target.value)}
          onBlur={applyDevId}
          onKeyDown={(e) => e.key === 'Enter' && applyDevId()}
          placeholder="devId"
        />
        <span className="spacer" />
        <ConnBadge />
        {user && (
          <span className="badge">
            {user.name} · {ROLE_LABEL[user.role]}
          </span>
        )}
        <button onClick={onLogout}>退出</button>
      </div>

      <div className="body">
        <nav className="sidenav">
          {NAV.filter((n) => user && isAtLeast(n.min)).map((n) => (
            <NavLink key={n.to} to={n.to}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <main className="content">
          <Outlet />
        </main>
      </div>

      {knownDevices.length > 0 && (
        <div className="content" style={{ paddingTop: 0 }}>
          <span className="muted" style={{ fontSize: 12 }}>
            已知设备：{knownDevices.join(' / ')}
          </span>
        </div>
      )}
    </div>
  );
}
