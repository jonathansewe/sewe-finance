/**
 * Shows an API error as a translated sentence, or nothing.
 *
 * The API sends stable codes (`invalid_credentials`, `rate_limited`, ...);
 * each has a key under `errors.` in en/fr/es.json. Unknown codes fall back
 * to a generic message. `accessibilityLiveRegion` makes screen readers
 * announce the error when it appears.
 */

import { StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { ApiError } from '@/lib/api';
import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

export function errorKey(error: unknown): string {
  return error instanceof ApiError ? `errors.${error.code}` : 'errors.unknown';
}

export function FormError({ error }: { error: unknown }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  if (!error) return null;
  return (
    <Text
      testID="form-error"
      accessibilityLiveRegion="polite"
      style={[styles.text, { color: colors.danger }]}
    >
      {t(errorKey(error), { defaultValue: t('errors.unknown') })}
    </Text>
  );
}

const styles = StyleSheet.create({
  text: { fontFamily: fonts.bodySemi, fontSize: size.small },
});
