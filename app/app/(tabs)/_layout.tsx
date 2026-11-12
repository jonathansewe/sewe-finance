/**
 * Tabs layout: the five main screens, switched by the floating island.
 *
 * File names in this folder become routes (index = Accounts). Expo Router
 * keeps each tab's state when you switch away and back. The tabs are for
 * signed-in users only: signed out → sign-in; two-factor off → its setup
 * (required before bank data, SPEC 6.2); then the one-time passkey offer.
 */

import { Redirect, Tabs } from 'expo-router';

import { useAuth } from '@/auth/AuthProvider';
import { IslandNav } from '@/components/IslandNav';

export default function TabsLayout() {
  const { status, me, shouldOfferPasskey } = useAuth();
  if (status === 'loading') return null;
  if (status === 'signedOut') return <Redirect href="/sign-in" />;
  if (me && !me.totp_enabled) return <Redirect href="/setup-totp" />;
  if (shouldOfferPasskey) return <Redirect href="/add-passkey" />;

  return (
    <Tabs tabBar={(props) => <IslandNav {...props} />} screenOptions={{ headerShown: false }}>
      <Tabs.Screen name="index" />
      <Tabs.Screen name="reports" />
      <Tabs.Screen name="receipt" />
      <Tabs.Screen name="chat" />
      <Tabs.Screen name="settings" />
    </Tabs>
  );
}
