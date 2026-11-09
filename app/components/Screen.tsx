/**
 * Page frame shared by every tab: background, header, scrolling content.
 *
 * Adds the 112 px bottom padding so the floating island never hides the
 * last item, and on wide web screens keeps a centered 480 px column
 * (SPEC 9), so V1 looks like a phone app on a laptop too.
 */

import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { layout } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

import { Header } from './Header';

export function Screen({ title, children }: { title: string; children: ReactNode }) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const wide = width > layout.wideBreakpoint;
  return (
    <SafeAreaView edges={['top']} style={[styles.root, { backgroundColor: colors.bg }]}>
      <View style={[styles.column, wide && styles.wideColumn]}>
        <Header title={title} />
        <ScrollView contentContainerStyle={styles.content}>{children}</ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  column: { flex: 1, width: '100%' },
  wideColumn: { maxWidth: layout.wideColumn, alignSelf: 'center' },
  content: { paddingHorizontal: 16, paddingBottom: layout.contentBottomPadding, gap: 12 },
});
