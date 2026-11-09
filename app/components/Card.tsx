/**
 * Card: the rounded surface most content sits on.
 *
 * `variant="hero"` uses the hero colors (cobalt in light mode, dark
 * surface in dark mode) for the big balance card.
 */

import type { ReactNode } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';

import { radius } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

type Props = { children: ReactNode; variant?: 'surface' | 'hero'; style?: ViewStyle };

export function Card({ children, variant = 'surface', style }: Props) {
  const { colors } = useTheme();
  const backgroundColor = variant === 'hero' ? colors.hero : colors.surface;
  return (
    <View style={[styles.card, { backgroundColor, borderColor: colors.line }, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: radius.card, padding: 20, gap: 12 },
});
