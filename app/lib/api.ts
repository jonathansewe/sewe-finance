/**
 * Typed client for the SEWE API. Every screen calls the API through here.
 *
 * - Adds `Authorization: Bearer <access token>` to signed-in calls.
 * - On a 401, refreshes the session once and retries. Parallel requests
 *   share ONE refresh (a single promise), so they don't race each other.
 * - Turns every error into `ApiError` with the API's stable `code`, which
 *   screens translate with t(`errors.${code}`).
 * - Sends cookies (`credentials: 'include'`) only to /auth/*: a browser
 *   ignores a Set-Cookie on a cross-origin response unless the request
 *   asked for credentials, and the cookie itself is scoped to
 *   /api/v1/auth/refresh, so it is never sent anywhere else.
 */

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
  usesRefreshCookie,
} from './tokens';

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

// --- Response types (mirror api/app/schemas) ---------------------------------

export type TokenResponse = {
  mfa_required: false;
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  refresh_token: string | null;
};
export type MfaRequired = { mfa_required: true; mfa_token: string; methods: ('totp' | 'recovery')[] };
export type Me = {
  email: string;
  display_name: string | null;
  totp_enabled: boolean;
  passkey_count: number;
};
export type Settings = { theme: 'dark' | 'light' | 'system'; language: 'en' | 'fr' | 'es' };
export type TotpSetup = { secret: string; otpauth_uri: string; qr_svg: string };
export type PasskeyOptions = { challenge_id: string; options: Record<string, unknown> };

// --- Core request ------------------------------------------------------------

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE';
type RequestOptions = { method?: Method; body?: unknown; auth?: boolean };

let sessionEndedHandler: () => void = () => {};

/** AuthProvider registers this so a failed refresh signs the app out. */
export function onSessionEnded(handler: () => void): void {
  sessionEndedHandler = handler;
}

async function send(path: string, options: RequestOptions, withAuth: boolean): Promise<Response> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  const access = getAccessToken();
  if (withAuth && access) headers.Authorization = `Bearer ${access}`;
  try {
    return await fetch(`${API_URL}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: path.startsWith('/auth/') ? 'include' : 'omit',
    });
  } catch {
    throw new ApiError(0, 'network_error', 'Could not reach the server');
  }
}

async function parse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (data as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ApiError(response.status, error?.code ?? 'unknown', error?.message ?? '');
  }
  return data as T;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const withAuth = options.auth ?? true;
  let response = await send(path, options, withAuth);
  if (response.status === 401 && withAuth && (await refreshSession())) {
    response = await send(path, options, withAuth);
  }
  return parse<T>(response);
}

// --- Refresh (one at a time) -------------------------------------------------

let refreshing: Promise<boolean> | null = null;

/** Get a new access token. Concurrent callers share the same attempt. */
export function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = doRefresh().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

async function doRefresh(): Promise<boolean> {
  let body: { refresh_token: string } | undefined;
  if (!usesRefreshCookie) {
    const stored = await getRefreshToken();
    if (!stored) return false;
    body = { refresh_token: stored };
  }
  try {
    const response = await send('/auth/refresh', { method: 'POST', body }, false);
    if (!response.ok) {
      await clearTokens();
      sessionEndedHandler();
      return false;
    }
    await storeTokens((await response.json()) as TokenResponse);
    return true;
  } catch {
    return false; // offline: keep the stored token and try again later
  }
}

export async function storeTokens(tokens: TokenResponse): Promise<void> {
  setAccessToken(tokens.access_token);
  if (tokens.refresh_token) await setRefreshToken(tokens.refresh_token);
}

// --- Endpoints ---------------------------------------------------------------

const post = <T>(path: string, body?: unknown, auth = false) =>
  request<T>(path, { method: 'POST', body, auth });

export const api = {
  signup: (email: string, password: string, language: string) =>
    post<{ status: 'verification_sent' }>('/auth/signup', { email, password, language }),
  verifyEmail: (email: string, code: string) =>
    post<TokenResponse>('/auth/verify-email', { email, code }),
  login: (email: string, password: string) =>
    post<TokenResponse | MfaRequired>('/auth/login', { email, password }),
  totpLogin: (mfaToken: string, code: string) =>
    post<TokenResponse>('/auth/totp/verify', { mfa_token: mfaToken, code }),
  recoveryLogin: (mfaToken: string, code: string) =>
    post<TokenResponse>('/auth/recovery/verify', { mfa_token: mfaToken, code }),
  totpSetup: () => post<TotpSetup>('/auth/totp/setup', undefined, true),
  totpConfirm: (code: string) =>
    post<{ recovery_codes: string[] }>('/auth/totp/verify', { code }, true),
  logout: () => post<void>('/auth/logout', undefined, true),
  me: () => request<Me>('/me'),
  getSettings: () => request<Settings>('/settings'),
  patchSettings: (patch: Partial<Settings>) =>
    request<Settings>('/settings', { method: 'PATCH', body: patch }),
  passkeyRegisterOptions: () =>
    post<PasskeyOptions>('/auth/passkey/register/options', undefined, true),
  passkeyRegisterVerify: (challengeId: string, credential: unknown, label: string) =>
    post<{ id: string; label: string }>(
      '/auth/passkey/register/verify',
      { challenge_id: challengeId, credential, label },
      true,
    ),
  passkeyLoginOptions: () => post<PasskeyOptions>('/auth/passkey/login/options'),
  passkeyLoginVerify: (challengeId: string, credential: unknown) =>
    post<TokenResponse>('/auth/passkey/login/verify', { challenge_id: challengeId, credential }),
};
