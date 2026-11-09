/**
 * Tests for the M1 exercise. By default they run against YOUR file
 * (my_resolveTheme.ts). CI sets SOLUTION=reference to run the same tests
 * against app/theme/resolveTheme.ts, which proves the tests are right.
 */

type Impl = (preference: string | null | undefined, system: string | null | undefined) => string;

const { resolveTheme } = (
  process.env.SOLUTION === 'reference'
    ? require('../../app/theme/resolveTheme')
    : require('./my_resolveTheme')
) as { resolveTheme: Impl };

describe('resolveTheme', () => {
  it.each([
    ['system', 'dark', 'dark'],
    ['system', 'light', 'light'],
  ])('follows the device when preference is %s (device %s)', (pref, system, expected) => {
    expect(resolveTheme(pref, system)).toBe(expected);
  });

  it.each([
    ['dark', 'light', 'dark'],
    ['light', 'dark', 'light'],
    ['dark', null, 'dark'],
  ])('explicit %s wins over device %s', (pref, system, expected) => {
    expect(resolveTheme(pref, system)).toBe(expected);
  });

  it.each([null, undefined, 'purple', ''])('unknown preference %p follows the device', (pref) => {
    expect(resolveTheme(pref, 'dark')).toBe('dark');
    expect(resolveTheme(pref, 'light')).toBe('light');
  });

  it('a device that reports nothing gets light', () => {
    expect(resolveTheme('system', null)).toBe('light');
    expect(resolveTheme('system', undefined)).toBe('light');
  });
});
