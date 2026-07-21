import { describe, it, expect } from 'vitest';
import { hasCapability, isRoleAtLeast, ROLE_CAPS } from '../src/auth/rbac';

describe('RBAC 三角色', () => {
  it('角色层级累进', () => {
    expect(isRoleAtLeast('operator', 'operator')).toBe(true);
    expect(isRoleAtLeast('operator', 'admin')).toBe(false);
    expect(isRoleAtLeast('engineer', 'operator')).toBe(true);
    expect(isRoleAtLeast('admin', 'engineer')).toBe(true);
    expect(isRoleAtLeast('admin', 'admin')).toBe(true);
  });

  it('operator 仅基础操作，不可 OTA/恢复出厂', () => {
    expect(hasCapability('operator', 'telemetry.view')).toBe(true);
    expect(hasCapability('operator', 'task.dispatch')).toBe(true);
    expect(hasCapability('operator', 'ota.trigger')).toBe(false);
    expect(hasCapability('operator', 'system.factory_reset')).toBe(false);
    expect(hasCapability('operator', 'config.param')).toBe(false);
  });

  it('engineer 可参数/SMDL/干扰点，但不可 OTA', () => {
    expect(hasCapability('engineer', 'config.param')).toBe(true);
    expect(hasCapability('engineer', 'config.smdl')).toBe(true);
    expect(hasCapability('engineer', 'interference.edit')).toBe(true);
    expect(hasCapability('engineer', 'ota.trigger')).toBe(false);
  });

  it('admin 拥有全部能力', () => {
    const allCaps = Array.from(new Set(Object.values(ROLE_CAPS).flat()));
    for (const c of allCaps) expect(hasCapability('admin', c)).toBe(true);
  });

  it('未登录无任何能力', () => {
    expect(hasCapability(null, 'telemetry.view')).toBe(false);
    expect(isRoleAtLeast(null, 'operator')).toBe(false);
  });
});
