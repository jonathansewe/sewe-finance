/**
 * One-time offer after signing in on the web: add a passkey, so next time
 * this browser signs in with a fingerprint, face or device PIN instead of
 * password + code. "Not now" is remembered on this device.
 */

import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { FormError } from '@/components/FormError';
import { Screen } from '@/components/Screen';
import { registerPasskey } from '@/lib/passkeys';
import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

export default function AddPasskeyScreen() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { dismissPasskeyOffer, reloadMe } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  function done() {
    dismissPasskeyOffer();
    router.replace('/');
  }

  async function add() {
    setBusy(true);
    setError(null);
    try {
      await registerPasskey(t('onboarding.passkeyLabel'));
      await reloadMe();
      done();
    } catch (e) {
      if (!(e instanceof Error && e.name === 'NotAllowedError')) setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title={t('onboarding.passkeyTitle')}>
      <Card style={styles.card}>
        <Text style={[styles.body, { color: colors.text }]}>{t('onboarding.passkeyBody')}</Text>
        <FormError error={error} />
        <Button label={t('onboarding.addPasskey')} busy={busy} onPress={add} testID="add-passkey" />
        <Button label={t('onboarding.notNow')} variant="secondary" onPress={done} testID="not-now" />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { gap: 14 },
  body: { fontFamily: fonts.body, fontSize: size.body },
});
