/**
 * Where tokens live (SPEC 6.1).
 *
 * The access token (15 minutes) is kept in memory only, on every platform:
 * a page reload forgets it, and /auth/refresh gets a new one.
 * The refresh token (30 days) depends on the platform:
 *  - web: an HttpOnly cookie the API sets. JavaScript never sees it, so an
 *    XSS bug can't steal it. Nothing to store here.
 *  - iOS/Android: expo-secure-store (Keychain / Keystore), sent in the
 *    body of /auth/refresh.
 */

import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const REFRESH_KEY = 'sewe.refreshToken';

/** True on web: the refresh token travels as a cookie, not in JSON. */
export const usesRefreshCookie = Platform.OS === 'web';

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export async function getRefreshToken(): Promise<string | null> {
  if (usesRefreshCookie) return null;
  try {
    return await SecureStore.getItemAsync(REFRESH_KEY);
  } catch {
    return null;
  }
}

export async function setRefreshToken(token: string): Promise<void> {
  if (usesRefreshCookie) return;
  await SecureStore.setItemAsync(REFRESH_KEY, token);
}

export async function clearTokens(): Promise<void> {
  accessToken = null;
  if (usesRefreshCookie) return;
  try {
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  } catch {
    // Nothing stored: already cleared.
  }
}
