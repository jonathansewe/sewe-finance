/**
 * Screen header: the title on the left, the sun/moon theme button on the right.
 *
 * The sun shows in dark mode ("switch to light") and the moon in light
 * mode. The button is 44×44 so it's an easy touch target.
 */

import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { fonts, layout, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

import { MoonIcon, SunIcon } from './icons';

export function Header({ title }: { title: string }) {
  const { t } = useTranslation();
  const { colors, theme, toggle } = useTheme();
  return (
    <View style={styles.header}>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {title}
      </Text>
      <Pressable
        onPress={toggle}
        accessibilityRole="button"
        accessibilityLabel={t('theme.toggle')}
        testID="theme-toggle"
        style={[styles.button, { borderColor: colors.line, backgroundColor: colors.surface }]}
      >
        {theme === 'dark' ? <SunIcon color={colors.text} /> : <MoonIcon color={colors.text} />}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    height: layout.headerHeight,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingLeft: 20,
    paddingRight: 16,
  },
  title: { fontFamily: fonts.heading, fontSize: size.title, letterSpacing: -0.3 },
  button: {
    width: layout.touchTarget,
    height: layout.touchTarget,
    borderRadius: layout.touchTarget / 2,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
