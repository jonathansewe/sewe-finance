/**
 * The real routes with a fake API: the auth guard, sign-in with a TOTP
 * code, translated errors, TOTP setup with recovery codes, sign out.
 */

import { act, fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import path from 'path';

import i18n from '@/i18n';

import {
  error,
  forgetSession,
  installFakeApi,
  ME,
  rememberSession,
  signedInRoutes,
  tokens,
} from './fakeApi';

const APP_DIR = path.resolve(__dirname, '../app');

beforeEach(async () => {
  await forgetSession();
});

afterEach(async () => {
  await act(async () => {
    await i18n.changeLanguage('en');
  });
});

it('signed out: the tabs redirect to sign-in', async () => {
  installFakeApi({});
  const router = await renderRouter(APP_DIR, { initialUrl: '/' });
  expect(await screen.findByTestId('sign-in')).toBeTruthy();
  expect(router.getPathname()).toBe('/sign-in');
});

it('password + TOTP code signs in and opens the tabs', async () => {
  const calls = installFakeApi({
    'POST /auth/login': {
      status: 200,
      json: { mfa_required: true, mfa_token: 'mfa-1', methods: ['totp', 'recovery'] },
    },
    'POST /auth/totp/verify': { status: 200, json: tokens() },
    'GET /me': { status: 200, json: ME },
    'GET /settings': { status: 200, json: { theme: 'system', language: 'en' } },
  });
  const router = await renderRouter(APP_DIR, { initialUrl: '/sign-in' });

  await fireEvent.changeText(await screen.findByTestId('email'), 'jo@example.com');
  await fireEvent.changeText(screen.getByTestId('password'), 'correct horse battery');
  await fireEvent.press(screen.getByTestId('sign-in'));

  expect(await screen.findByText('Enter the code from your authenticator app.')).toBeTruthy();
  expect(router.getPathname()).toBe('/two-factor');
  // The MFA token is kept in memory, not in the URL.
  expect(JSON.stringify(router.getSearchParams())).not.toContain('mfa-1');

  await fireEvent.changeText(screen.getByTestId('code'), '123 456');
  await fireEvent.press(screen.getByTestId('verify'));

  expect(await screen.findByTestId('tab-index')).toBeTruthy();
  expect(calls.find((c) => c.path === '/auth/totp/verify')?.body).toEqual({
    mfa_token: 'mfa-1',
    code: '123456',
  });
});

it('a wrong password shows the translated error', async () => {
  installFakeApi({ 'POST /auth/login': error(401, 'invalid_credentials') });
  await renderRouter(APP_DIR, { initialUrl: '/sign-in' });
  await act(async () => {
    await i18n.changeLanguage('fr');
  });

  await fireEvent.changeText(await screen.findByTestId('email'), 'jo@example.com');
  await fireEvent.changeText(screen.getByTestId('password'), 'wrong');
  await fireEvent.press(screen.getByTestId('sign-in'));

  expect(await screen.findByText('E-mail ou mot de passe incorrect.')).toBeTruthy();
});

it('an account without TOTP must set it up, then sees recovery codes once', async () => {
  await rememberSession();
  let totpOn = false;
  installFakeApi(
    signedInRoutes({
      'GET /me': () => ({ status: 200, json: { ...ME, totp_enabled: totpOn } }),
      'POST /auth/totp/setup': {
        status: 200,
        json: { secret: 'JBSWY3DPEHPK3PXP', otpauth_uri: 'otpauth://totp/x', qr_svg: '<svg/>' },
      },
      'POST /auth/totp/verify': () => {
        totpOn = true;
        return { status: 200, json: { recovery_codes: ['abcd-efgh-jkmn', 'pqrs-tvwx-yz01'] } };
      },
    }),
  );
  const router = await renderRouter(APP_DIR, { initialUrl: '/' });

  expect(await screen.findByTestId('totp-secret')).toHaveTextContent('JBSW Y3DP EHPK 3PXP');
  expect(router.getPathname()).toBe('/setup-totp');

  await fireEvent.changeText(screen.getByTestId('code'), '123456');
  await fireEvent.press(screen.getByTestId('totp-confirm'));
  expect(await screen.findByText('abcd-efgh-jkmn')).toBeTruthy();

  await fireEvent.press(screen.getByTestId('recovery-saved'));
  expect(await screen.findByTestId('tab-index')).toBeTruthy();
});

it('sign out in Settings ends the session and returns to sign-in', async () => {
  await rememberSession();
  const calls = installFakeApi(signedInRoutes());
  const router = await renderRouter(APP_DIR, { initialUrl: '/settings' });

  expect(await screen.findByText('Signed in as jo@example.com')).toBeTruthy();
  await fireEvent.press(screen.getByTestId('sign-out'));

  expect(await screen.findByTestId('sign-in')).toBeTruthy();
  expect(router.getPathname()).toBe('/sign-in');
  expect(calls.some((c) => c.method === 'POST' && c.path === '/auth/logout')).toBe(true);
});

it('changing the theme while signed in saves it to the account', async () => {
  await rememberSession();
  const calls = installFakeApi(signedInRoutes());
  await renderRouter(APP_DIR, { initialUrl: '/settings' });

  await fireEvent.press(await screen.findByTestId('theme-picker-dark'));

  await act(async () => {}); // let the sync effect run
  expect(calls.find((c) => c.method === 'PATCH' && c.path === '/settings')?.body).toEqual({
    theme: 'dark',
  });
});
