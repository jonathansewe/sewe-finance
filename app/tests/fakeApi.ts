/**
 * A fake SEWE API for tests: replaces global fetch with a route table.
 *
 * Each route is "METHOD /path" → a response, or a function of the request.
 * Every call is recorded, so tests can check what the app sent.
 */

import * as SecureStore from 'expo-secure-store';

import { API_URL, type Me, type TokenResponse } from '@/lib/api';
import { clearTokens } from '@/lib/tokens';

type Call = {
  method: string;
  path: string;
  body: unknown;
  headers: Record<string, string>;
  credentials?: RequestCredentials;
};
type Reply = { status: number; json?: unknown };
type Route = Reply | ((call: Call) => Reply);

export const tokens = (access = 'access-1', refresh = 'sid.refresh-1'): TokenResponse => ({
  mfa_required: false,
  access_token: access,
  token_type: 'bearer',
  expires_in: 900,
  refresh_token: refresh,
});

export const ME: Me = {
  email: 'jo@example.com',
  display_name: null,
  totp_enabled: true,
  passkey_count: 0,
};

export const error = (status: number, code: string): Reply => ({
  status,
  json: { error: { code, message: code } },
});

export function installFakeApi(routes: Record<string, Route>): Call[] {
  const calls: Call[] = [];
  global.fetch = jest.fn(async (url: string | URL | Request, init: RequestInit = {}) => {
    const call: Call = {
      method: init.method ?? 'GET',
      path: String(url).replace(API_URL, ''),
      body: typeof init.body === 'string' ? JSON.parse(init.body) : undefined,
      headers: (init.headers ?? {}) as Record<string, string>,
      credentials: init.credentials,
    };
    calls.push(call);
    const route = routes[`${call.method} ${call.path}`];
    const reply = typeof route === 'function' ? route(call) : (route ?? error(404, 'not_found'));
    return {
      ok: reply.status < 400,
      status: reply.status,
      json: async () => reply.json,
    } as Response;
  }) as typeof fetch;
  return calls;
}

/** Routes for an already signed-in user with TOTP on (the default `me`). */
export function signedInRoutes(overrides: Record<string, Route> = {}): Record<string, Route> {
  return {
    'POST /auth/refresh': { status: 200, json: tokens() },
    'GET /me': { status: 200, json: ME },
    'GET /settings': { status: 200, json: { theme: 'system', language: 'en' } },
    'PATCH /settings': (call) => ({
      status: 200,
      json: { theme: 'system', language: 'en', ...(call.body as object) },
    }),
    'POST /auth/logout': { status: 204 },
    ...overrides,
  };
}

/** Pretend a previous run saved a refresh token (native platforms). */
export async function rememberSession(): Promise<void> {
  await SecureStore.setItemAsync('sewe.refreshToken', 'sid.refresh-0');
}

export async function forgetSession(): Promise<void> {
  await clearTokens();
}
