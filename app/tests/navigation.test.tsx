/**
 * The real app routes render: the island shows 5 tabs, tapping one
 * navigates, and changing the language in Settings relabels the tabs.
 * The tabs need a signed-in user, so a fake API restores a session.
 */

import { act, fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import path from 'path';

import i18n from '@/i18n';

import { installFakeApi, rememberSession, signedInRoutes } from './fakeApi';

const APP_DIR = path.resolve(__dirname, '../app');

beforeEach(async () => {
  await rememberSession();
  installFakeApi(signedInRoutes());
});

afterEach(async () => {
  await act(async () => {
    await i18n.changeLanguage('en');
  });
});

it('shows five tabs and opens Settings', async () => {
  const router = await renderRouter(APP_DIR, { initialUrl: '/' });

  expect(await screen.findByTestId('tab-index')).toBeTruthy();
  for (const name of ['index', 'reports', 'receipt', 'chat', 'settings']) {
    expect(screen.getByTestId(`tab-${name}`)).toBeTruthy();
  }
  expect(screen.getByTestId('tab-index')).toBeSelected();

  await fireEvent.press(screen.getByTestId('tab-settings'));

  expect(router.getPathname()).toBe('/settings');
  expect(screen.getByTestId('tab-settings')).toBeSelected();
});

it('switching language in Settings relabels the island', async () => {
  await renderRouter(APP_DIR, { initialUrl: '/settings' });
  expect(await screen.findByTestId('tab-index')).toHaveTextContent('Accounts');

  await fireEvent.press(screen.getByTestId('language-picker-fr'));
  expect(await screen.findByText('Comptes')).toBeTruthy();

  await fireEvent.press(screen.getByTestId('language-picker-es'));
  expect(await screen.findByText('Cuentas')).toBeTruthy();
});
