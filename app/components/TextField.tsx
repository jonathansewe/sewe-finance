/**
 * Labelled text input in the design's field style (radius 12, 48 px tall).
 *
 * The label is a real accessibility label, so screen readers announce it.
 * `autoComplete` lets password managers fill email, password and
 * one-time codes (SMS/TOTP autofill uses "one-time-code").
 */

import { StyleSheet, Text, TextInput, type TextInputProps, View } from 'react-native';

import { fonts, radius, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

type Props = Omit<TextInputProps, 'style'> & { label: string };

export function TextField({ label, ...input }: Props) {
  const { colors } = useTheme();
  return (
    <View style={styles.field}>
      <Text style={[styles.label, { color: colors.muted }]}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.muted}
        autoCapitalize="none"
        autoCorrect={false}
        {...input}
        style={[
          styles.input,
          { backgroundColor: colors.field, borderColor: colors.fieldLine, color: colors.text },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: 6 },
  label: { fontFamily: fonts.bodySemi, fontSize: size.tiny },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderRadius: radius.input,
    paddingHorizontal: 14,
    fontFamily: fonts.body,
    fontSize: size.body,
  },
});
