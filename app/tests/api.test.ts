/**
 * The API client: one shared refresh on 401, error codes, cookie scope.
 */

import { api, ApiError, onSessionEnded } from '@/lib/api';
import { getAccessToken, setAccessToken } from '@/lib/tokens';

import { error, forgetSession, installFakeApi, ME, rememberSession, tokens } from './fakeApi';

beforeEach(async () => {
  await forgetSession();
});

it('parallel 401s share a single refresh, then retry with the new token', async () => {
  await rememberSession();
  setAccessToken('expired');
  const calls = installFakeApi({
    'GET /me': (call) =>
      call.headers.Authorization === 'Bearer fresh'
        ? { status: 200, json: ME }
        : error(401, 'invalid_token'),
    'POST /auth/refresh': { status: 200, json: tokens('fresh', 'sid.refresh-2') },
  });

  const [a, b] = await Promise.all([api.me(), api.me()]);

  expect(a.email).toBe('jo@example.com');
  expect(b.email).toBe('jo@example.com');
  expect(calls.filter((c) => c.path === '/auth/refresh')).toHaveLength(1);
  // Native: the stored refresh token goes in the body, not a cookie.
  expect(calls.find((c) => c.path === '/auth/refresh')?.body).toEqual({
    refresh_token: 'sid.refresh-0',
  });
  expect(getAccessToken()).toBe('fresh');
});

it('a failed refresh clears tokens and tells the app the session ended', async () => {
  await rememberSession();
  setAccessToken('expired');
  installFakeApi({
    'GET /me': error(401, 'invalid_token'),
    'POST /auth/refresh': error(401, 'refresh_reused'),
  });
  const ended = jest.fn();
  onSessionEnded(ended);

  await expect(api.me()).rejects.toMatchObject({ status: 401 });
  expect(ended).toHaveBeenCalledTimes(1);
  expect(getAccessToken()).toBeNull();
});

it('errors carry the API code for translation', async () => {
  installFakeApi({ 'POST /auth/login': error(401, 'invalid_credentials') });
  const failure = api.login('jo@example.com', 'nope');
  await expect(failure).rejects.toBeInstanceOf(ApiError);
  await expect(failure).rejects.toMatchObject({ code: 'invalid_credentials' });
});

it('a network failure becomes network_error', async () => {
  global.fetch = jest.fn(async () => {
    throw new TypeError('Failed to fetch');
  }) as typeof fetch;
  await expect(api.getSettings()).rejects.toMatchObject({ code: 'network_error' });
});

it('sends cookies only to /auth/* and never sends a Bearer token to sign-in calls', async () => {
  setAccessToken('a-token');
  const calls = installFakeApi({
    'POST /auth/login': { status: 200, json: tokens() },
    'GET /settings': { status: 200, json: { theme: 'dark', language: 'fr' } },
  });
  await api.login('jo@example.com', 'correct horse');
  await api.getSettings();

  const [login, settings] = calls;
  expect(login.credentials).toBe('include');
  expect(login.headers.Authorization).toBeUndefined();
  expect(settings.credentials).toBe('omit');
  expect(settings.headers.Authorization).toBe('Bearer a-token');
});
