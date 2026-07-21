/**
 * JWT HS256 —— 基于 Web Crypto（crypto.subtle HMAC-SHA256）。
 *
 * 说明：
 *  - 浏览器/安卓 WebView 在 secure context（https / localhost / Capacitor https scheme）下可用 crypto.subtle。
 *  - signToken 用于「演示用」本地签发；真实环境由认证服务器签发，客户端仅 verifyToken 做路由守卫。
 *  - 解码位运算与 OTA schema.py 无关；此处仅处理认证令牌。
 */
import type { Role } from './rbac';

export interface JwtPayload {
  sub?: string;
  name?: string;
  role: Role;
  iat?: number;
  exp?: number;
  [k: string]: unknown;
}

function strToBytes(s: string): Uint8Array {
  // 包一层 ArrayBuffer 支撑的 Uint8Array，满足 crypto.subtle 的 BufferSource 约束
  return new Uint8Array(new TextEncoder().encode(s));
}
function bytesToStr(b: Uint8Array): string {
  return new TextDecoder().decode(b);
}
function bytesToB64url(bytes: Uint8Array): string {
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function b64urlToBytes(s: string): Uint8Array {
  const b64 = s.replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function importKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'raw',
    strToBytes(secret) as unknown as BufferSource,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign', 'verify'],
  );
}

/** 签发 HS256 JWT */
export async function signToken(payload: JwtPayload, secret: string): Promise<string> {
  const header = { alg: 'HS256', typ: 'JWT' };
  const h = bytesToB64url(strToBytes(JSON.stringify(header)));
  const p = bytesToB64url(strToBytes(JSON.stringify(payload)));
  const data = strToBytes(`${h}.${p}`);
  const key = await importKey(secret);
  const sig = await crypto.subtle.sign('HMAC', key, data as unknown as BufferSource);
  const s = bytesToB64url(new Uint8Array(sig));
  return `${h}.${p}.${s}`;
}

/** 校验 HS256 JWT 签名并返回 payload；失败返回 null */
export async function verifyToken(token: string, secret: string): Promise<JwtPayload | null> {
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const [h, p, s] = parts;
  const data = strToBytes(`${h}.${p}`);
  try {
    const key = await importKey(secret);
    const ok = await crypto.subtle.verify(
      'HMAC',
      key,
      b64urlToBytes(s) as unknown as BufferSource,
      data as unknown as BufferSource,
    );
    if (!ok) return null;
    const payload = JSON.parse(bytesToStr(b64urlToBytes(p))) as JwtPayload;
    if (typeof payload.exp === 'number' && payload.exp * 1000 < Date.now()) return null;
    if (!payload.role) return null;
    return payload;
  } catch {
    return null;
  }
}

/** 解码 payload（不校验签名），用于展示过期等；失败返回 null */
export function decodeUnsafe(token: string): JwtPayload | null {
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  try {
    return JSON.parse(bytesToStr(b64urlToBytes(parts[1]))) as JwtPayload;
  } catch {
    return null;
  }
}
