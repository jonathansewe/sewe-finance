/**
 * Stroke icons copied from the design canvas (24×24 viewBox, 1.8 stroke).
 *
 * Drawn with react-native-svg so the same code renders on web, iOS and
 * Android. Icons are decorative: the button around each one carries the
 * accessible label.
 */

import type { ReactNode } from 'react';
import Svg, { Circle, Path } from 'react-native-svg';

type IconProps = { color: string; size?: number };

function Base({ size = 20, children }: { size?: number; children: ReactNode }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      {children}
    </Svg>
  );
}

const stroke = (color: string) =>
  ({ stroke: color, strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }) as const;

export function HomeIcon({ color, size }: IconProps) {
  return (
    <Base size={size}>
      <Path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" {...stroke(color)} />
    </Base>
  );
}

export function ReportsIcon({ color, size }: IconProps) {
  return (
    <Base size={size}>
      <Path d="M5 20V11M11 20V5M17 20v-7M2 20h20" {...stroke(color)} />
    </Base>
  );
}

export function ReceiptIcon({ color, size }: IconProps) {
  return (
    <Base size={size}>
      <Path d="M4 8h3l2-3h6l2 3h3v12H4z" {...stroke(color)} />
      <Circle cx="12" cy="13" r="4" {...stroke(color)} />
    </Base>
  );
}

export function ChatIcon({ color, size }: IconProps) {
  return (
    <Base size={size}>
      <Path d="M4 5h16v11H9l-5 4z" {...stroke(color)} />
    </Base>
  );
}

export function SettingsIcon({ color, size }: IconProps) {
  return (
    <Base size={size}>
      <Circle cx="12" cy="12" r="3" {...stroke(color)} />
      <Path
        d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"
        {...stroke(color)}
      />
    </Base>
  );
}

export function SunIcon({ color, size }: IconProps) {
  return (
    <Base size={size}>
      <Circle cx="12" cy="12" r="4" {...stroke(color)} />
      <Path
        d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
        {...stroke(color)}
      />
    </Base>
  );
}

export function MoonIcon({ color, size }: IconProps) {
  return (
    <Base size={size}>
      <Path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" {...stroke(color)} />
    </Base>
  );
}
