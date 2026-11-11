/**
 * Sign in: a passkey (web, once this browser has one: the default) or
 * email + password. A password login on an account with TOTP goes on to
 * the two-factor screen; an unverified email goes to the code screen.
 */

import { Link, router } from 'expo-router';
import { useEffect, useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { FormError } from '@/components/FormError';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { api, ApiError } from '@/lib/api';
import { deviceHasPasskey, passkeysSupported, signInWithPasskey } from '@/lib/passkeys';
import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

export default function SignInScreen() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { completeSignIn, setMfaToken, setPendingEmail } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState<'password' | 'passkey' | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [passkeyFirst, setPasskeyFirst] = useState(false);
  const canPasskey = passkeysSupported();

  useEffect(() => {
    if (canPasskey) void deviceHasPasskey().then(setPasskeyFirst);
  }, [canPasskey]);

  async function withPassword() {
    setBusy('password');
    setError(null);
    try {
      const result = await api.login(email, password);
      if (result.mfa_required) {
        setMfaToken(result.mfa_token);
        router.push('/two-factor');
      } else {
        await completeSignIn(result);
      }
    } catch (e) {
      if (e instanceof ApiError && e.code === 'email_not_verified') {
        setPendingEmail(email.trim().toLowerCase());
        router.push('/verify-email');
      } else {
        setError(e);
      }
    } finally {
      setBusy(null);
    }
  }

  async function withPasskey() {
    setBusy('passkey');
    setError(null);
    try {
      await completeSignIn(await signInWithPasskey());
    } catch (e) {
      // The user closing the browser's passkey dialog isn't an error worth showing.
      if (!(e instanceof Error && e.name === 'NotAllowedError')) setError(e);
    } finally {
      setBusy(null);
    }
  }

  const passkeyButton = canPasskey ? (
    <Button
      label={t('auth.signInWithPasskey')}
      variant={passkeyFirst ? 'primary' : 'secondary'}
      busy={busy === 'passkey'}
      onPress={withPasskey}
      testID="passkey-sign-in"
    />
  ) : null;

  return (
    <Screen title={t('auth.signInTitle')}>
      {passkeyFirst && passkeyButton}
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
          autoComplete="current-password"
          testID="password"
        />
        <FormError error={error} />
        <Button
          label={t('auth.signIn')}
          variant={passkeyFirst ? 'secondary' : 'primary'}
          busy={busy === 'password'}
          disabled={!email || !password}
          onPress={withPassword}
          testID="sign-in"
        />
      </Card>
      {!passkeyFirst && passkeyButton}
      <Text style={[styles.footer, { color: colors.muted }]}>
        {t('auth.noAccount')}{' '}
        <Link href="/sign-up" style={{ color: colors.accentText }}>
          {t('auth.createAccount')}
        </Link>
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { gap: 14 },
  footer: { fontFamily: fonts.body, fontSize: size.small, textAlign: 'center' },
});
