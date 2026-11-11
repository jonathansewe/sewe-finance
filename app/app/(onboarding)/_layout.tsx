/**
 * Signed-in setup screens that come before the tabs: turning on TOTP
 * (required before bank data, SPEC 6.2) and the one-time passkey offer.
 */

import { Redirect, Stack } from 'expo-router';

import { useAuth } from '@/auth/AuthProvider';

export default function OnboardingLayout() {
  const { status } = useAuth();
  if (status === 'loading') return null;
  if (status === 'signedOut') return <Redirect href="/sign-in" />;
  return <Stack screenOptions={{ headerShown: false }} />;
}
