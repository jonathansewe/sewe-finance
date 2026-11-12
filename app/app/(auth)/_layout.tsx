/**
 * Signed-out screens: sign in, sign up, verify email, two-factor code.
 *
 * Once signed in, this group sends you to the tabs; the tabs layout then
 * decides whether TOTP setup or the passkey offer comes first.
 */

import { Redirect, Stack } from 'expo-router';

import { useAuth } from '@/auth/AuthProvider';

export default function AuthLayout() {
  const { status } = useAuth();
  if (status === 'loading') return null;
  if (status === 'signedIn') return <Redirect href="/" />;
  return <Stack screenOptions={{ headerShown: false }} />;
}
