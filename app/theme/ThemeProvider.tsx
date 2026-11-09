/**
 * Theme context: which theme is active, and a way to change it.
 *
 * Holds the user's preference (system / dark / light), resolves it against
 * the device setting, and gives components the matching palette through
 * `useTheme()`. Changing the preference re-renders instantly; no reload.
 */

import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import { useColorScheme } from 'react-native';

import { readPreference, STORAGE_KEYS, writePreference } from '@/lib/storage';

import { isThemePreference, resolveTheme, type ThemePreference } from './resolveTheme';
import { type Palette, palettes, type ThemeName } from './tokens';

type ThemeContextValue = {
  preference: ThemePreference;
  theme: ThemeName;
  colors: Palette;
  setPreference: (next: ThemePreference) => void;
  toggle: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemScheme = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>('system');

  // Load the saved preference once at startup.
  useEffect(() => {
    void readPreference(STORAGE_KEYS.theme).then((saved) => {
      if (isThemePreference(saved)) setPreferenceState(saved);
    });
  }, []);

  const value = useMemo<ThemeContextValue>(() => {
    const theme = resolveTheme(preference, systemScheme);
    const setPreference = (next: ThemePreference) => {
      setPreferenceState(next);
      void writePreference(STORAGE_KEYS.theme, next);
    };
    return {
      preference,
      theme,
      colors: palettes[theme],
      setPreference,
      // The header button flips what you SEE, so it stores an explicit choice.
      toggle: () => setPreference(theme === 'dark' ? 'light' : 'dark'),
    };
  }, [preference, systemScheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error('useTheme must be used inside <ThemeProvider>');
  return value;
}
