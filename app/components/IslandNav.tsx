/**
 * The floating "island" tab bar (SPEC 9, design canvas "Final V1").
 *
 * Expo Router's <Tabs> handles routing; this component only draws the bar.
 * It gets the navigation state through `tabBar={(props) => <IslandNav />}`,
 * draws one button per route, and highlights the active one with a pill.
 */

import type { BottomTabBarProps } from 'expo-router/js-tabs';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { fonts, layout, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

import { ChatIcon, HomeIcon, ReceiptIcon, ReportsIcon, SettingsIcon } from './icons';

// Route file name → icon and translation key. Order follows the routes.
const TABS = {
  index: { Icon: HomeIcon, label: 'tabs.accounts' },
  reports: { Icon: ReportsIcon, label: 'tabs.reports' },
  receipt: { Icon: ReceiptIcon, label: 'tabs.receipt' },
  chat: { Icon: ChatIcon, label: 'tabs.chat' },
  settings: { Icon: SettingsIcon, label: 'tabs.settings' },
} as const;

type TabName = keyof typeof TABS;
const isTabName = (name: string): name is TabName => name in TABS;

export function IslandNav({ state, emitter, navigateToTab }: BottomTabBarProps) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  // On wide web screens, sit inside the same 480 px column as the content.
  const side =
    width > layout.wideBreakpoint ? (width - layout.wideColumn) / 2 + layout.islandSide : layout.islandSide;

  return (
    <View
      accessibilityRole="tablist"
      style={[
        styles.island,
        { left: side, right: side, backgroundColor: colors.island, borderColor: colors.islandLine },
      ]}
    >
      {state.routes.map((route, index) => {
        if (!isTabName(route.name)) return null;
        const { Icon, label } = TABS[route.name];
        const active = state.index === index;
        const fg = active ? colors.islandActiveText : colors.islandText;
        const onPress = () => {
          // Let screens cancel the switch (React Navigation convention).
          const event = emitter.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
          if (!active && !event.defaultPrevented) navigateToTab(route.key);
        };
        return (
          <Pressable
            key={route.key}
            onPress={onPress}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            accessibilityLabel={t(label)}
            testID={`tab-${route.name}`}
            style={[styles.tab, active && { backgroundColor: colors.islandActive }]}
          >
            <Icon color={fg} />
            <Text style={[styles.label, { color: fg }]} numberOfLines={1}>
              {t(label)}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  island: {
    position: 'absolute',
    bottom: layout.islandBottom,
    height: layout.islandHeight,
    borderRadius: layout.islandHeight / 2,
    borderWidth: 1,
    padding: 6,
    flexDirection: 'row',
    gap: 2,
    boxShadow: '0 8px 24px rgba(11,16,35,0.18)',
  },
  tab: {
    flex: 1,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 2,
  },
  label: { fontFamily: fonts.bodyBold, fontSize: size.nav },
});
