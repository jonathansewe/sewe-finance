/**
 * Root layout: wraps every screen in the app-wide providers.
 *
 * Loads the fonts (Inter, Space Grotesk), starts i18n, and provides the
 * theme and the auth state. Expo Router renders the matching route inside
 * <Slot />; the group layouts ((auth), (onboarding), (tabs)) decide who may
 * see which screen. AuthProvider sits inside ThemeProvider so it can sync
 * the theme to the account.
 */

import '@/i18n';

import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold, Inter_700Bold } from '@expo-google-fonts/inter';
import {
  SpaceGrotesk_600SemiBold,
  SpaceGrotesk_700Bold,
} from '@expo-google-fonts/space-grotesk';
import { useFonts } from 'expo-font';
import { Slot } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '@/auth/AuthProvider';
import { ThemeProvider, useTheme } from '@/theme/ThemeProvider';

export { ErrorBoundary } from 'expo-router';

function ThemedStatusBar() {
  const { theme } = useTheme();
  return <StatusBar style={theme === 'dark' ? 'light' : 'dark'} />;
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    SpaceGrotesk_600SemiBold,
    SpaceGrotesk_700Bold,
  });
  // Render once fonts are ready, or anyway if they failed (system fallback).
  if (!fontsLoaded && !fontError) return null;

  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AuthProvider>
          <ThemedStatusBar />
          <Slot />
        </AuthProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
