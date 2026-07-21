import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { DEMO_HINTS } from '../auth/mockUsers';

export function LoginPage() {
  const { login, status, error } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const ok = await login(username, password);
    if (ok) navigate('/dashboard', { replace: true });
  };

  return (
    <div className="login-wrap">
      <div className="card login-card">
        <h3>XLPS2 HMI 登录</h3>
        <form onSubmit={onSubmit}>
          <label className="field">
            <span>用户名</span>
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          </label>
          <label className="field">
            <span>密码</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && <div className="badge err">{error}</div>}
          <button
            className="primary"
            type="submit"
            disabled={status === 'authenticating'}
            style={{ width: '100%' }}
          >
            {status === 'authenticating' ? '登录中…' : '登录'}
          </button>
        </form>
        <div className="hint">
          演示账号（生产应由认证服务器签发 JWT）：
          <br />
          {DEMO_HINTS.map((h) => `${h.username} / ${h.password}（${h.name}）`).join('　·　')}
        </div>
      </div>
    </div>
  );
}
