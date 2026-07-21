/**
 * 认证 Provider / Hook。
 * - useAuth() 即 zustand authStore 的 hook（含 can / isAtLeast）。
 * - AuthProvider 在挂载时执行 restore() 恢复会话。
 */
import { useEffect } from 'react';
import { useAuthStore } from '../store/authStore';

export function useAuth() {
  return useAuthStore();
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const restore = useAuthStore((s) => s.restore);
  const status = useAuthStore((s) => s.status);

  useEffect(() => {
    if (status === 'idle') void restore();
    // 仅初始化执行一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <>{children}</>;
}
