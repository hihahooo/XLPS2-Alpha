import { Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../auth/AuthContext';
import type { Role } from '../auth/rbac';

/** 未登录 → 跳登录页 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const user = useAuth().user;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** 角色低于 min → 跳设备总览（无权限兜底） */
export function RequireRole({ min, children }: { min: Role; children: ReactNode }) {
  const { user, isAtLeast } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!isAtLeast(min)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
