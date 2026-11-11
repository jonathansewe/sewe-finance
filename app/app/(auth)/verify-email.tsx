/**
 * Enter the 6-digit code from the email. A right code signs you in.
 *
 * Codes last 10 minutes and allow 5 tries. For a new code, sign up again
 * with the same email (the API resends; nothing else changes).
 */

import { Redirect } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { FormError } from '@/components/FormError';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { api } from '@/lib/api';
import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

export default function VerifyEmailScreen() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { pendingEmail, completeSignIn } = useAuth();
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  // Opened directly (e.g. after a reload): there's no email to verify.
  if (!pendingEmail) return <Redirect href="/sign-up" />;

  async function submit() {
    if (!pendingEmail) return;
    setBusy(true);
    setError(null);
    try {
      await completeSignIn(await api.verifyEmail(pendingEmail, code.trim()));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title={t('auth.verifyTitle')}>
      <Card style={styles.card}>
        <Text style={[styles.body, { color: colors.text }]}>
          {t('auth.verifyBody', { email: pendingEmail })}
        </Text>
        <TextField
          label={t('auth.code')}
          value={code}
          onChangeText={setCode}
          keyboardType="number-pad"
          autoComplete="one-time-code"
          maxLength={6}
          testID="code"
        />
        <FormError error={error} />
        <Button
          label={t('auth.verify')}
          busy={busy}
          disabled={code.trim().length !== 6}
          onPress={submit}
          testID="verify"
        />
        <Text style={[styles.hint, { color: colors.muted }]}>{t('auth.verifyResend')}</Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { gap: 14 },
  body: { fontFamily: fonts.body, fontSize: size.body },
  hint: { fontFamily: fonts.body, fontSize: size.small },
});
