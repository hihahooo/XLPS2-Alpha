/**
 * 三角色 RBAC（operator / engineer / admin）
 *
 * - operator：现场操作（监控 / 任务下发 / 诊断查看 / 审计查看与上报）
 * - engineer：+ 干扰点编辑 / 参数热调(param/set) / SMDL 下发(config/smdl)
 * - admin：+ OTA 触发(ota/cmd,ota/data) / 恢复出厂(factory_reset)
 *
 * 规则：角色具备其自身及低阶角色的全部能力（层级累进）。
 */

export type Role = 'operator' | 'engineer' | 'admin';

export type Capability =
  | 'telemetry.view'
  | 'task.dispatch'
  | 'diag.view'
  | 'audit.view'
  | 'audit.publish'
  | 'interference.edit'
  | 'config.param'
  | 'config.smdl'
  | 'ota.trigger'
  | 'system.factory_reset';

export const ROLE_RANK: Record<Role, number> = {
  operator: 1,
  engineer: 2,
  admin: 3,
};

export const ROLE_LABEL: Record<Role, string> = {
  operator: '操作员',
  engineer: '维护工程师',
  admin: '系统管理员',
};

export const ROLE_CAPS: Record<Role, Capability[]> = {
  operator: ['telemetry.view', 'task.dispatch', 'diag.view', 'audit.view', 'audit.publish'],
  engineer: [
    'telemetry.view',
    'task.dispatch',
    'diag.view',
    'audit.view',
    'audit.publish',
    'interference.edit',
    'config.param',
    'config.smdl',
  ],
  admin: [
    'telemetry.view',
    'task.dispatch',
    'diag.view',
    'audit.view',
    'audit.publish',
    'interference.edit',
    'config.param',
    'config.smdl',
    'ota.trigger',
    'system.factory_reset',
  ],
};

/** 判断角色是否拥有某能力 */
export function hasCapability(role: Role | null, cap: Capability): boolean {
  if (!role) return false;
  return ROLE_CAPS[role].includes(cap);
}

/** 判断角色是否达到最低角色要求（层级比较） */
export function isRoleAtLeast(role: Role | null, min: Role): boolean {
  if (!role) return false;
  return ROLE_RANK[role] >= ROLE_RANK[min];
}

/** 路由 → 最低角色要求（路由守卫依据） */
export const ROUTE_MIN_ROLE: Record<string, Role> = {
  '/dashboard': 'operator',
  '/tasks': 'operator',
  '/diagnostics': 'operator',
  '/audit': 'operator',
  '/interference': 'engineer',
  '/config': 'engineer',
  '/ota': 'admin',
};

/** 受 admin 约束的敏感操作（用于 UI 显隐 + 二次确认） */
export const ADMIN_ONLY_CAPS: Capability[] = ['ota.trigger', 'system.factory_reset'];
