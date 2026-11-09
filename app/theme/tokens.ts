/**
 * Design tokens: every color, size and radius the UI uses (SPEC 9).
 *
 * Components read from here and never hard-code hex values, so a design
 * change happens in one file and both themes always stay complete. The
 * `Palette` type forces dark and light to define exactly the same keys.
 */

export type ThemeName = 'dark' | 'light';

export type Palette = {
  bg: string;
  surface: string;
  line: string;
  field: string;
  fieldLine: string;
  text: string;
  muted: string;
  chip: string;
  chipText: string;
  accent: string;
  accentText: string;
  onAccent: string;
  accentSoft: string;
  accentSoftText: string;
  hero: string;
  heroText: string;
  heroSub: string;
  heroTile: string;
  frame: string;
  frameLine: string;
  island: string;
  islandLine: string;
  islandText: string;
  islandActive: string;
  islandActiveText: string;
  danger: string;
};

export const palettes: Record<ThemeName, Palette> = {
  dark: {
    bg: '#0F1115',
    surface: '#191C22',
    line: '#262A31',
    field: '#0F1115',
    fieldLine: '#333842',
    text: '#F2F3F5',
    muted: '#A0A6B1',
    chip: '#262A31',
    chipText: '#D4D8DE',
    accent: '#B8F24A',
    accentText: '#B8F24A',
    onAccent: '#0F1115',
    accentSoft: '#262A31',
    accentSoftText: '#B8F24A',
    hero: '#191C22',
    heroText: '#F2F3F5',
    heroSub: '#A0A6B1',
    heroTile: '#262A31',
    frame: '#000000',
    frameLine: '#B8F24A',
    island: '#20242B',
    islandLine: '#2E333B',
    islandText: '#A0A6B1',
    islandActive: '#B8F24A',
    islandActiveText: '#0F1115',
    danger: '#FF8A7A',
  },
  light: {
    bg: '#F3F5FA',
    surface: '#FFFFFF',
    line: '#E6EAF2',
    field: '#F3F5FA',
    fieldLine: '#E6EAF2',
    text: '#0B1023',
    muted: '#5A6275',
    chip: '#EEF1F7',
    chipText: '#3B4357',
    accent: '#2340D3',
    accentText: '#2340D3',
    onAccent: '#FFFFFF',
    accentSoft: '#E3E8FB',
    accentSoftText: '#1A31A8',
    hero: '#2340D3',
    heroText: '#FFFFFF',
    heroSub: '#DDE3FB',
    heroTile: 'rgba(255,255,255,0.14)',
    frame: '#0B1023',
    frameLine: '#8FA2F0',
    island: '#0B1023',
    islandLine: '#0B1023',
    islandText: '#C9CFE0',
    islandActive: '#2340D3',
    islandActiveText: '#FFFFFF',
    danger: '#C2261A',
  },
};

export const fonts = {
  heading: 'SpaceGrotesk_700Bold',
  headingSemi: 'SpaceGrotesk_600SemiBold',
  body: 'Inter_400Regular',
  bodyMedium: 'Inter_500Medium',
  bodySemi: 'Inter_600SemiBold',
  bodyBold: 'Inter_700Bold',
} as const;

export const size = {
  bigNumber: 40,
  title: 21,
  section: 16,
  body: 15,
  small: 13,
  tiny: 12,
  nav: 10,
} as const;

export const radius = { card: 24, cardSmall: 20, input: 12, pill: 999 } as const;

export const layout = {
  headerHeight: 64,
  islandHeight: 68,
  islandSide: 12,
  islandBottom: 16,
  contentBottomPadding: 112, // so the floating island never covers content
  wideBreakpoint: 900,
  wideColumn: 480,
  touchTarget: 44,
} as const;
