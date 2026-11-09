/**
 * "Coming soon" card for tabs whose feature arrives in a later milestone.
 *
 * Keeps the M1 navigation real (every tab opens a themed, translated
 * screen) without building features early.
 */

import { StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

import { Card } from './Card';

export function Placeholder({ milestone }: { milestone: string }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  return (
    <Card>
      <Text style={[styles.title, { color: colors.text }]}>{t('placeholder.title')}</Text>
      <Text style={[styles.body, { color: colors.muted }]}>
        {t('placeholder.body', { milestone })}
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: fonts.heading, fontSize: 20 },
  body: { fontFamily: fonts.body, fontSize: size.body - 1, lineHeight: 21 },
});
