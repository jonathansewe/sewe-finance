/**
 * Pill button: `primary` (accent fill) or `secondary` (chip fill).
 *
 * While `busy`, it shows a spinner and ignores taps, so a slow network
 * can't send the same form twice. At least 48 px tall (touch target).
 */

import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { fonts, radius, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

type Props = {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary';
  busy?: boolean;
  disabled?: boolean;
  testID?: string;
};

export function Button({ label, onPress, variant = 'primary', busy, disabled, testID }: Props) {
  const { colors } = useTheme();
  const primary = variant === 'primary';
  const inactive = busy || disabled;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: inactive, busy }}
      disabled={inactive}
      onPress={onPress}
      testID={testID}
      style={[
        styles.button,
        { backgroundColor: primary ? colors.accent : colors.chip, opacity: disabled ? 0.5 : 1 },
      ]}
    >
      {busy ? (
        <ActivityIndicator color={primary ? colors.onAccent : colors.chipText} />
      ) : (
        <Text style={[styles.label, { color: primary ? colors.onAccent : colors.chipText }]}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: 48,
    borderRadius: radius.pill,
    paddingHorizontal: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: { fontFamily: fonts.bodyBold, fontSize: size.body },
});
