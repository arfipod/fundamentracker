import type { SVGProps } from 'react';

export type IconName =
  | 'signals'
  | 'watchlist'
  | 'explorer'
  | 'refresh'
  | 'scan'
  | 'settings'
  | 'sun'
  | 'moon'
  | 'table'
  | 'grid'
  | 'chart'
  | 'pause'
  | 'play'
  | 'trash'
  | 'close'
  | 'plus'
  | 'check'
  | 'database'
  | 'sparkles'
  | 'tag'
  | 'search'
  | 'clock'
  | 'chevronDown';

interface IconProps extends Omit<SVGProps<SVGSVGElement>, 'name'> {
  name: IconName;
  size?: number;
}

export function Icon({ name, size = 18, ...props }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      {...props}
    >
      {iconPath(name)}
    </svg>
  );
}

function iconPath(name: IconName) {
  switch (name) {
    case 'signals':
      return <><path d="M4 17V7" /><path d="M8 14v-4" /><path d="M12 18V6" /><path d="M16 15V9" /><path d="M20 12v-1" /></>;
    case 'watchlist':
      return <><path d="M8 6h13" /><path d="M8 12h13" /><path d="M8 18h13" /><path d="M3 6h.01" /><path d="M3 12h.01" /><path d="M3 18h.01" /></>;
    case 'explorer':
      return <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /><path d="m8.5 13.5 2-5 2 3 2-1" /></>;
    case 'refresh':
      return <><path d="M20 11a8 8 0 0 0-14.9-4" /><path d="M4 4v5h5" /><path d="M4 13a8 8 0 0 0 14.9 4" /><path d="M20 20v-5h-5" /></>;
    case 'scan':
      return <><path d="M4 7V4h3" /><path d="M17 4h3v3" /><path d="M20 17v3h-3" /><path d="M7 20H4v-3" /><path d="M7 12h10" /></>;
    case 'settings':
      return <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4v-.2a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" /></>;
    case 'sun':
      return <><circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" /><path d="m4.9 4.9 1.4 1.4" /><path d="m17.7 17.7 1.4 1.4" /><path d="M2 12h2" /><path d="M20 12h2" /><path d="m6.3 17.7-1.4 1.4" /><path d="m19.1 4.9-1.4 1.4" /></>;
    case 'moon':
      return <path d="M20.5 15.2A8.5 8.5 0 0 1 8.8 3.5 8.6 8.6 0 1 0 20.5 15.2Z" />;
    case 'table':
      return <><rect x="3" y="4" width="18" height="16" rx="1" /><path d="M3 10h18" /><path d="M9 4v16" /></>;
    case 'grid':
      return <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>;
    case 'chart':
      return <><path d="M3 3v18h18" /><path d="m7 15 4-4 3 2 5-6" /></>;
    case 'pause':
      return <><path d="M9 5v14" /><path d="M15 5v14" /></>;
    case 'play':
      return <path d="m8 5 11 7-11 7Z" />;
    case 'trash':
      return <><path d="M4 7h16" /><path d="m9 7 .7-3h4.6l.7 3" /><path d="m6 7 1 14h10l1-14" /><path d="M10 11v6" /><path d="M14 11v6" /></>;
    case 'close':
      return <><path d="m6 6 12 12" /><path d="m18 6-12 12" /></>;
    case 'plus':
      return <><path d="M12 5v14" /><path d="M5 12h14" /></>;
    case 'check':
      return <path d="m5 12 4 4L19 6" />;
    case 'database':
      return <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7" /></>;
    case 'sparkles':
      return <><path d="m12 3 1.2 3.3L16.5 7.5l-3.3 1.2L12 12l-1.2-3.3-3.3-1.2 3.3-1.2Z" /><path d="m18 13 .8 2.2L21 16l-2.2.8L18 19l-.8-2.2L15 16l2.2-.8Z" /><path d="m6 14 .7 1.8 1.8.7-1.8.7L6 19l-.7-1.8-1.8-.7 1.8-.7Z" /></>;
    case 'tag':
      return <><path d="M20 13 11 22l-9-9V4h9Z" /><circle cx="7" cy="9" r="1.5" /></>;
    case 'search':
      return <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>;
    case 'clock':
      return <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>;
    case 'chevronDown':
      return <path d="m7 9 5 5 5-5" />;
  }
}
