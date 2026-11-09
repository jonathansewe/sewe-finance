/**
 * Accounts tab (home). M1 shows the empty state from the design canvas;
 * real balances and transactions arrive with statement import in M3.
 */

import { Pressable, StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { Card } from '@/components/Card';
import { Screen } from '@/components/Screen';
import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

export default function AccountsScreen() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  return (
    <Screen title={t('titles.accounts')}>
      <Card variant="hero">
        <Text style={[styles.small, { color: colors.heroSub }]}>{t('accounts.totalBalance')}</Text>
        <Text style={[styles.big, { color: colors.heroText }]}>—</Text>
      </Card>
      <Card>
        <Text style={[styles.cardTitle, { color: colors.text }]}>{t('accounts.emptyTitle')}</Text>
        <Text style={[styles.body, { color: colors.muted }]}>{t('accounts.emptyBody')}</Text>
        {/* Disabled until M3 builds the import flow. */}
        <Pressable
          disabled
          accessibilityRole="button"
          accessibilityState={{ disabled: true }}
          style={[styles.primary, { backgroundColor: colors.accent, opacity: 0.5 }]}
        >
          <Text style={[styles.buttonText, { color: colors.onAccent }]}>
            {t('accounts.importStatement')}
          </Text>
        </Pressable>
        <Pressable
          disabled
          accessibilityRole="button"
          accessibilityState={{ disabled: true }}
          style={[styles.secondary, { borderColor: colors.line }]}
        >
          <Text style={[styles.buttonText, { color: colors.muted }]}>{t('accounts.connectBank')}</Text>
        </Pressable>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  small: { fontFamily: fonts.body, fontSize: size.small },
  big: { fontFamily: fonts.heading, fontSize: 42 },
  cardTitle: { fontFamily: fonts.heading, fontSize: 20 },
  body: { fontFamily: fonts.body, fontSize: 14, lineHeight: 21 },
  primary: { height: 50, borderRadius: 999, alignItems: 'center', justifyContent: 'center' },
  secondary: {
    height: 50,
    borderRadius: 999,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: { fontFamily: fonts.bodyBold, fontSize: size.body },
});
