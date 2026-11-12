/**
 * Turn on two-factor: scan the QR code with an authenticator app, type the
 * code it shows, then save the 10 recovery codes. They are shown once
 * only: the server keeps just their hashes.
 */

import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SvgXml } from 'react-native-svg';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { FormError } from '@/components/FormError';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { api, ApiError, type TotpSetup } from '@/lib/api';
import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

export default function SetupTotpScreen() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { reloadMe } = useAuth();
  const [setup, setSetup] = useState<TotpSetup | null>(null);
  const [code, setCode] = useState('');
  const [recovery, setRecovery] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const started = useRef(false);

  useEffect(() => {
    // Each /totp/setup call makes a NEW secret. React runs effects twice in
    // development, so guard: otherwise the QR shown might not be the one saved.
    if (started.current) return;
    started.current = true;
    api
      .totpSetup()
      .then(setSetup)
      .catch(async (e: unknown) => {
        // Already on (another tab finished setup): just carry on.
        if (e instanceof ApiError && e.code === 'totp_already_enabled') {
          await reloadMe();
          router.replace('/');
        } else {
          setError(e);
        }
      });
  }, [reloadMe]);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      setRecovery((await api.totpConfirm(code.replace(/\s/g, ''))).recovery_codes);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    await reloadMe(); // totp_enabled is now true, so the tabs open
    router.replace('/');
  }

  if (recovery) {
    return (
      <Screen title={t('onboarding.recoveryTitle')}>
        <Card style={styles.card}>
          <Text style={[styles.body, { color: colors.text }]}>{t('onboarding.recoveryBody')}</Text>
          <View style={styles.codes} testID="recovery-codes">
            {recovery.map((c) => (
              <Text key={c} selectable style={[styles.code, { color: colors.text }]}>
                {c}
              </Text>
            ))}
          </View>
          <Button label={t('onboarding.recoverySaved')} onPress={finish} testID="recovery-saved" />
        </Card>
      </Screen>
    );
  }

  return (
    <Screen title={t('onboarding.totpTitle')}>
      <Card style={styles.card}>
        <Text style={[styles.body, { color: colors.text }]}>{t('onboarding.totpBody')}</Text>
        {setup && (
          <>
            {/* QR codes need dark-on-light to scan, so keep a white tile in both themes. */}
            <View
              style={styles.qr}
              accessible
              accessibilityRole="image"
              accessibilityLabel={t('onboarding.qrLabel')}
            >
              <SvgXml xml={setup.qr_svg} width={200} height={200} />
            </View>
            <Text style={[styles.hint, { color: colors.muted }]}>{t('onboarding.manualKey')}</Text>
            <Text selectable style={[styles.code, { color: colors.text }]} testID="totp-secret">
              {setup.secret.replace(/(.{4})/g, '$1 ').trim()}
            </Text>
          </>
        )}
        <TextField
          label={t('auth.code')}
          value={code}
          onChangeText={setCode}
          keyboardType="number-pad"
          autoComplete="one-time-code"
          maxLength={7}
          testID="code"
        />
        <FormError error={error} />
        <Button
          label={t('onboarding.turnOn')}
          busy={busy}
          disabled={!setup || code.replace(/\s/g, '').length !== 6}
          onPress={confirm}
          testID="totp-confirm"
        />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { gap: 14 },
  body: { fontFamily: fonts.body, fontSize: size.body },
  hint: { fontFamily: fonts.body, fontSize: size.small },
  qr: {
    alignSelf: 'center',
    padding: 8,
    borderRadius: 12,
    backgroundColor: '#FFFFFF', // scanner contrast, intentionally theme-independent
  },
  codes: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  code: { fontFamily: fonts.bodySemi, fontSize: size.body, letterSpacing: 1 },
});
