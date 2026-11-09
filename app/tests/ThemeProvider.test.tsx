/** The theme context resolves, toggles, and remembers the user's choice. */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { Pressable, Text } from 'react-native';

import { STORAGE_KEYS } from '@/lib/storage';
import { palettes } from '@/theme/tokens';
import { ThemeProvider, useTheme } from '@/theme/ThemeProvider';

function Probe() {
  const { theme, preference, colors, toggle, setPreference } = useTheme();
  return (
    <>
      <Text testID="state">{`${preference}/${theme}/${colors.bg}`}</Text>
      <Pressable testID="toggle" onPress={toggle} />
      <Pressable testID="system" onPress={() => setPreference('system')} />
    </>
  );
}

beforeEach(async () => {
  await AsyncStorage.clear();
});

it('toggle flips what is shown and stores an explicit choice', async () => {
  await render(
    <ThemeProvider>
      <Probe />
    </ThemeProvider>,
  );
  const before = screen.getByTestId('state').props.children as string;
  const startTheme = before.split('/')[1] as 'dark' | 'light';
  const flipped = startTheme === 'dark' ? 'light' : 'dark';

  await fireEvent.press(screen.getByTestId('toggle'));

  expect(screen.getByTestId('state')).toHaveTextContent(`${flipped}/${flipped}/${palettes[flipped].bg}`);
  await waitFor(async () => expect(await AsyncStorage.getItem(STORAGE_KEYS.theme)).toBe(flipped));
});

it('restores a saved preference on startup', async () => {
  await AsyncStorage.setItem(STORAGE_KEYS.theme, 'dark');
  await render(
    <ThemeProvider>
      <Probe />
    </ThemeProvider>,
  );
  await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent(`dark/dark/${palettes.dark.bg}`));
});

it('ignores a corrupted saved value', async () => {
  await AsyncStorage.setItem(STORAGE_KEYS.theme, 'purple');
  await render(
    <ThemeProvider>
      <Probe />
    </ThemeProvider>,
  );
  await act(async () => {});
  expect(screen.getByTestId('state').props.children).toMatch(/^system\//);
});
