/**
 * Sign up: email + password. The API emails a 6-digit code in the app's
 * current language; the next screen asks for it. The answer is the same
 * whether or not the email already has an account (the API never says).
 */

import { Link, router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { FormError } from '@/components/FormError';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { isLanguage } from '@/i18n';
import { api } from '@/lib/api';
import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

const MIN_PASSWORD = 10;

export default function SignUpScreen() {
  const { t, i18n } = useTranslation();
  const { colors } = useTheme();
  const { setPendingEmail } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.signup(email, password, isLanguage(i18n.language) ? i18n.language : 'en');
      setPendingEmail(email.trim().toLowerCase());
      router.push('/verify-email');
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title={t('auth.signUpTitle')}>
      <Card style={styles.card}>
        <TextField
          label={t('auth.email')}
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoComplete="email"
          testID="email"
        />
        <TextField
          label={t('auth.password')}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="new-password"
          testID="password"
        />
        <Text style={[styles.hint, { color: colors.muted }]}>
          {t('auth.passwordHint', { min: MIN_PASSWORD })}
        </Text>
        <FormError error={error} />
        <Button
          label={t('auth.createAccount')}
          busy={busy}
          disabled={!email || password.length < MIN_PASSWORD}
          onPress={submit}
          testID="sign-up"
        />
      </Card>
      <Text style={[styles.hint, styles.center, { color: colors.muted }]}>
        {t('auth.haveAccount')}{' '}
        <Link href="/sign-in" style={{ color: colors.accentText }}>
          {t('auth.signIn')}
        </Link>
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { gap: 14 },
  hint: { fontFamily: fonts.body, fontSize: size.small },
  center: { textAlign: 'center' },
});
