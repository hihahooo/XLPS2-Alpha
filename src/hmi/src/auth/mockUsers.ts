/**
 * 演示用本地用户表（仅开发/演示；生产由认证服务器校验并签发 JWT）。
 * 密码为明文占位，严禁用于生产。
 */
import type { Role } from './rbac';

export interface DemoUser {
  password: string;
  role: Role;
  name: string;
}

export const DEMO_USERS: Record<string, DemoUser> = {
  operator: { password: 'op123', role: 'operator', name: '现场操作员' },
  engineer: { password: 'eng123', role: 'engineer', name: '维护工程师' },
  admin: { password: 'adm123', role: 'admin', name: '系统管理员' },
};

/** 演示账号提示（登录页展示） */
export const DEMO_HINTS = Object.entries(DEMO_USERS).map(([u, d]) => ({
  username: u,
  password: d.password,
  role: d.role,
  name: d.name,
}));
