/**
 * 认证状态（Zustand）——JWT HS256 + 三角色 RBAC。
 * 登录流程（演示）：本地校验凭证 → 本地签发 JWT → 持久化 token；
 * 启动恢复：读取本地 token → 校验签名/过期 → 还原会话。
 * 生产环境应改为「向认证服务器登录取得 token」，verifyToken 改为服务端公钥校验。
 */
import { create } from 'zustand';
import { APP_CONFIG } from '../config';
import { DEMO_USERS } from '../auth/mockUsers';
import { signToken, verifyToken, type JwtPayload } from '../auth/jwt';
import {
  hasCapability,
  isRoleAtLeast,
  type Capability,
  type Role,
} from '../auth/rbac';
import { readString, writeString, removeKey } from '../auth/storage';

export interface AuthUser {
  username: string;
  name: string;
  role: Role;
}

interface AuthStore {
  user: AuthUser | null;
  token: string | null;
  status: 'idle' | 'authenticating' | 'ready' | 'error';
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  restore: () => Promise<void>;
  can: (cap: Capability) => boolean;
  isAtLeast: (role: Role) => boolean;
}

function persist(token: string) {
  writeString(APP_CONFIG.storageKeys.token, token);
}
function clearPersisted() {
  removeKey(APP_CONFIG.storageKeys.token);
}

function userFromPayload(p: JwtPayload, username: string): AuthUser {
  return { username, name: p.name ?? username, role: p.role };
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  token: null,
  status: 'idle',
  error: null,

  login: async (username, password) => {
    set({ status: 'authenticating', error: null });
    const u = DEMO_USERS[username.trim()];
    if (!u || u.password !== password) {
      set({ status: 'error', error: '用户名或密码错误' });
      return false;
    }
    const now = Math.floor(Date.now() / 1000);
    const payload: JwtPayload = {
      sub: username,
      name: u.name,
      role: u.role,
      iat: now,
      exp: now + APP_CONFIG.auth.tokenTtlSec,
    };
    const token = await signToken(payload, APP_CONFIG.auth.jwtSecret);
    persist(token);
    set({ user: userFromPayload(payload, username), token, status: 'ready', error: null });
    return true;
  },

  logout: () => {
    clearPersisted();
    set({ user: null, token: null, status: 'idle', error: null });
  },

  restore: async () => {
    const token = readString(APP_CONFIG.storageKeys.token);
    if (!token) {
      set({ status: 'idle' });
      return;
    }
    const payload = await verifyToken(token, APP_CONFIG.auth.jwtSecret);
    if (!payload || !payload.sub) {
      clearPersisted();
      set({ user: null, token: null, status: 'idle' });
      return;
    }
    set({ user: userFromPayload(payload, payload.sub), token, status: 'ready' });
  },

  can: (cap) => hasCapability(get().user?.role ?? null, cap),
  isAtLeast: (role) => isRoleAtLeast(get().user?.role ?? null, role),
}));
