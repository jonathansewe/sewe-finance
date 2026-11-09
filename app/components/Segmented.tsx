/**
 * Segmented control: a pill row where exactly one option is selected.
 *
 * Used for theme and language in Settings, and later for report periods.
 * Generic over the value type, so `onChange` gets e.g. 'dark' | 'light'
 * instead of a plain string.
 */

import { Pressable, StyleSheet, Text, View } from 'react-native';

import { fonts, size } from '@/theme/tokens';
import { useTheme } from '@/theme/ThemeProvider';

type Option<T extends string> = { value: T; label: string };

type Props<T extends string> = {
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  testID?: string;
};

export function Segmented<T extends string>({ options, value, onChange, testID }: Props<T>) {
  const { colors } = useTheme();
  return (
    <View
      accessibilityRole="radiogroup"
      testID={testID}
      style={[styles.row, { backgroundColor: colors.chip }]}
    >
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <Pressable
            key={option.value}
            onPress={() => onChange(option.value)}
            accessibilityRole="radio"
            accessibilityState={{ checked: selected }}
            testID={testID ? `${testID}-${option.value}` : undefined}
            style={[styles.option, selected && { backgroundColor: colors.accent }]}
          >
            <Text
              style={[
                styles.label,
                {
                  color: selected ? colors.onAccent : colors.chipText,
                  fontFamily: selected ? fonts.bodyBold : fonts.bodySemi,
                },
              ]}
            >
              {option.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 4, padding: 4, borderRadius: 999 },
  option: { flex: 1, minHeight: 44, borderRadius: 999, alignItems: 'center', justifyContent: 'center' },
  label: { fontSize: size.small },
});
