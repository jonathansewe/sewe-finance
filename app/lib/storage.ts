/**
 * Small wrapper around AsyncStorage for device-local preferences.
 *
 * Theme and language are saved here (localStorage on web) so they apply
 * before sign-in; once signed in, they also sync to the account (M2).
 * Failures are swallowed on purpose: private browsing can block storage,
 * and a lost preference is harmless. Never store tokens here.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

export const STORAGE_KEYS = {
  theme: 'sewe.themePreference',
  language: 'sewe.language',
  hasPasskey: 'sewe.hasPasskey', // this browser has signed in with a passkey
  passkeyOfferDismissed: 'sewe.passkeyOfferDismissed',
} as const;

export async function readPreference(key: string): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(key);
  } catch {
    return null;
  }
}

export async function writePreference(key: string, value: string): Promise<void> {
  try {
    await AsyncStorage.setItem(key, value);
  } catch {
    // Storage unavailable: the choice still applies for this session.
  }
}
