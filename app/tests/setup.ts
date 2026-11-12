// Jest setup: in-memory stand-ins for device features, so app code runs
// without a phone or a browser.
/* eslint-disable @typescript-eslint/no-require-imports -- jest.mock factories must be synchronous */

// AsyncStorage (device preferences).
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

// expo-secure-store (the native refresh token): a Map, cleared per test file.
jest.mock('expo-secure-store', () => {
  const store = new Map<string, string>();
  return {
    getItemAsync: jest.fn(async (key: string) => store.get(key) ?? null),
    setItemAsync: jest.fn(async (key: string, value: string) => {
      store.set(key, value);
    }),
    deleteItemAsync: jest.fn(async (key: string) => {
      store.delete(key);
    }),
  };
});

// WebAuthn exists only in real browsers; tests run as "no passkey support".
jest.mock('@simplewebauthn/browser', () => ({
  browserSupportsWebAuthn: () => false,
  startRegistration: jest.fn(),
  startAuthentication: jest.fn(),
}));
