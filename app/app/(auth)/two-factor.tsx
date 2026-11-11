/**
 * Second sign-in step: the 6-digit code from the authenticator app, or a
 * one-time recovery code if the phone is lost.
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

export default function TwoFactorScreen() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { mfaToken, completeSignIn } = useAuth();
  const [useRecovery, setUseRecovery] = useState(false);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  if (!mfaToken) return <Redirect href="/sign-in" />;

  async function submit() {
    if (!mfaToken) return;
    setBusy(true);
    setError(null);
    try {
      const tokens = useRecovery
        ? await api.recoveryLogin(mfaToken, code)
        : await api.totpLogin(mfaToken, code.replace(/\s/g, ''));
      await completeSignIn(tokens);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title={t('auth.twoFactorTitle')}>
      <Card style={styles.card}>
        <Text style={[styles.body, { color: colors.text }]}>
          {t(useRecovery ? 'auth.recoveryBody' : 'auth.twoFactorBody')}
        </Text>
        <TextField
          label={t(useRecovery ? 'auth.recoveryCode' : 'auth.code')}
          value={code}
          onChangeText={setCode}
          keyboardType={useRecovery ? 'default' : 'number-pad'}
          autoComplete={useRecovery ? 'off' : 'one-time-code'}
          testID="code"
        />
        <FormError error={error} />
        <Button label={t('auth.verify')} busy={busy} disabled={!code} onPress={submit} testID="verify" />
        <Button
          label={t(useRecovery ? 'auth.useAuthenticator' : 'auth.useRecovery')}
          variant="secondary"
          onPress={() => {
            setUseRecovery(!useRecovery);
            setCode('');
            setError(null);
          }}
          testID="toggle-recovery"
        />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { gap: 14 },
  body: { fontFamily: fonts.body, fontSize: size.body },
});
