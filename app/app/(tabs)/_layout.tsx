/**
 * Tabs layout: the five main screens, switched by the floating island.
 *
 * File names in this folder become routes (index = Accounts). Expo Router
 * keeps each tab's state when you switch away and back.
 */

import { Tabs } from 'expo-router';

import { IslandNav } from '@/components/IslandNav';

export default function TabsLayout() {
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
