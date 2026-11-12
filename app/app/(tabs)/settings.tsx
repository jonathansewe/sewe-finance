/**
 * Settings tab: Appearance (theme, language) and, from M2, who is signed
 * in plus Sign out. Theme and language sync to the account through
 * AuthProvider. Active sessions, passkeys and recovery codes join the
 * Security section in M8; Data and AI sections arrive with their milestones.
 */

import Constants from 'expo-constants';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Screen } from '@/components/Screen';
import { Segmented } from '@/components/Segmented';
import { isLanguage, type Language, LANGUAGES, setLanguage } from '@/i18n';
import type { ThemePreference } from '@/theme/resolveTheme';
import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

const THEME_OPTIONS: ThemePreference[] = ['system', 'dark', 'light'];

export default function SettingsScreen() {
  const { t, i18n } = useTranslation();
  const { colors, preference, setPreference } = useTheme();
  const { me, signOut } = useAuth();
  const language: Language = isLanguage(i18n.language) ? i18n.language : 'en';

  return (
    <Screen title={t('titles.settings')}>
      <Text style={[styles.section, { color: colors.muted }]}>{t('settings.appearance')}</Text>
      <Card style={styles.card}>
        <View style={styles.field}>
          <Text style={[styles.label, { color: colors.text }]}>{t('settings.theme')}</Text>
          <Segmented
            testID="theme-picker"
            value={preference}
            onChange={setPreference}
            options={THEME_OPTIONS.map((value) => ({ value, label: t(`theme.${value}`) }))}
          />
        </View>
        <View style={styles.field}>
          <Text style={[styles.label, { color: colors.text }]}>{t('settings.language')}</Text>
          <Segmented
            testID="language-picker"
            value={language}
            onChange={setLanguage}
            options={LANGUAGES.map((value) => ({ value, label: t(`languages.${value}`) }))}
          />
        </View>
      </Card>
      <Text style={[styles.section, { color: colors.muted }]}>{t('settings.security')}</Text>
      <Card style={styles.card}>
        {me && (
          <Text style={[styles.label, { color: colors.text }]}>
            {t('settings.signedInAs', { email: me.email })}
          </Text>
        )}
        <Text style={[styles.value, { color: colors.muted }]}>{t('settings.twoFactorOn')}</Text>
        <Button label={t('settings.signOut')} variant="secondary" onPress={signOut} testID="sign-out" />
      </Card>
      <Text style={[styles.version, { color: colors.muted }]}>
        {t('settings.version', { version: Constants.expoConfig?.version ?? '0.0.0' })}
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  section: { fontFamily: fonts.bodyBold, fontSize: size.tiny, letterSpacing: 0.6, marginTop: 2 },
  card: { padding: 16, gap: 16 },
  field: { gap: 8 },
  label: { fontFamily: fonts.bodySemi, fontSize: 14 },
  value: { fontFamily: fonts.body, fontSize: size.small },
  version: { fontFamily: fonts.body, fontSize: 11, textAlign: 'center' },
});
