/**
 * Turn the user's theme preference into the theme to draw.
 *
 * The preference can be "system", which means "whatever the device says".
 * This function is pure (no React, no storage), so it's easy to test and is
 * the M1 rewrite exercise (exercises/M1).
 */

import type { ThemeName } from './tokens';

export type ThemePreference = 'system' | 'dark' | 'light';

export function resolveTheme(
  preference: string | null | undefined,
  systemScheme: string | null | undefined,
): ThemeName {
  if (preference === 'dark' || preference === 'light') {
    return preference;
  }
  // "system", missing, or an unknown saved value: follow the device.
  // Devices that report nothing get light, the browser default.
  return systemScheme === 'dark' ? 'dark' : 'light';
}

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === 'system' || value === 'dark' || value === 'light';
}
