import type { CSSProperties, ReactNode } from "react";

const paths: Record<string, ReactNode> = {
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  arrowLeft: <path d="M19 12H5M11 6l-6 6 6 6" />,
  check: <path d="M20 6 9 17l-5-5" />,
  checkCircle: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </>
  ),
  play: <path d="M6 4l14 8-14 8z" fill="currentColor" stroke="none" />,
  thumbsUp: (
    <path d="M7 10v11H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1zm0 0 4.5-7a2 2 0 0 1 1.8 2.9L12 10h6a2 2 0 0 1 2 2.3l-1 6A2 2 0 0 1 17 21H7" />
  ),
  chevron: <path d="m6 9 6 6 6-6" />,
  chevronRight: <path d="m9 6 6 6-6 6" />,
  star: (
    <path
      d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"
      fill="currentColor"
      stroke="none"
    />
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  gauge: (
    <>
      <path d="M12 13l4-3" />
      <circle cx="12" cy="13" r="8" />
      <path d="M12 5v1M5 13H4M20 13h-1" />
    </>
  ),
  wrench: (
    <path d="M14.7 6.3a4 4 0 0 0-5.4 5.2L4 17l3 3 5.5-5.3a4 4 0 0 0 5.2-5.4l-2.4 2.4-2.3-.6-.6-2.3z" />
  ),
  book: <path d="M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2zM4 19h14" />,
  users: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20a6 6 0 0 1 12 0M16 5.5a3 3 0 0 1 0 5.8M21 20a6 6 0 0 0-4-5.6" />
    </>
  ),
  award: (
    <>
      <circle cx="12" cy="9" r="5" />
      <path d="M9 13.5 8 21l4-2 4 2-1-7.5" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
  power: (
    <>
      <path d="M12 3v9" />
      <path d="M7.5 6.5a7 7 0 1 0 9 0" />
    </>
  ),
  key: (
    <>
      <circle cx="8" cy="15" r="4" />
      <path d="M10.8 12.2 20 3M16 7l3 3M14 9l2 2" />
    </>
  ),
  file: (
    <>
      <path d="M14 3v5h5" />
      <path d="M14 3H6v18h12V8z" />
    </>
  ),
  message: <path d="M21 12a8 8 0 0 1-11.5 7.2L4 20l1.2-4.8A8 8 0 1 1 21 12z" />,
  x: <path d="M6 6l12 12M18 6 6 18" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 9h18M8 3v4M16 3v4" />
    </>
  ),
  phone: (
    <path d="M5 4h4l2 5-3 2a12 12 0 0 0 5 5l2-3 5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" />
  ),
  spark: (
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />
  ),
  bolt: (
    <path d="M13 3 4 14h6l-1 7 9-11h-6z" fill="currentColor" stroke="none" />
  ),
  infinity: (
    <path d="M6 9a3 3 0 1 0 0 6c2 0 3-1.5 6-3s4-3 6-3a3 3 0 1 1 0 6c-2 0-3-1.5-6-3S8 9 6 9z" />
  ),
  download: <path d="M12 3v12m-5-5 5 5 5-5M5 21h14" />,
  youtube: (
    <>
      <rect x="2" y="5" width="20" height="14" rx="4" />
      <path d="M10 9l5 3-5 3z" fill="currentColor" stroke="none" />
    </>
  ),
  instagram: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="0.6" fill="currentColor" />
    </>
  ),
  threads: (
    <path d="M16 8.5c-1-1.7-2.5-2.5-4.2-2.5C9 6 7 8.3 7 12s2 6 4.8 6c2 0 3.7-1.2 3.7-3.2 0-2-1.6-3-3.6-3-1.3 0-2.4.6-2.4 1.8 0 .9.7 1.5 1.6 1.5 1.3 0 2.1-1 2.1-2.8" />
  ),
  pin: (
    <>
      <path d="M12 21s7-5.5 7-11a7 7 0 0 0-14 0c0 5.5 7 11 7 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3.5 7 8.5 6 8.5-6" />
    </>
  ),
  sparkle4: (
    <path
      d="M12 2c.5 5 1.8 7.5 8 8-6.2.5-7.5 3-8 8-.5-5-1.8-7.5-8-8 6.2-.5 7.5-3 8-8z"
      fill="currentColor"
      stroke="none"
    />
  ),
  whatsapp: (
    <>
      <path d="M3 21l1.7-4.1A8 8 0 1 1 8 19.3L3 21z" />
      <path d="M9 9c0 3 2.5 5.5 5.5 5.5.5 0 .9-.4.9-.8 0-.3-1.2-1-1.5-1-.3 0-.5.4-.7.6-.6-.3-1.2-.9-1.5-1.5.2-.2.6-.4.6-.7 0-.3-.7-1.5-1-1.5-.4 0-.8.4-.8.9z" />
    </>
  ),
  linkedin: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <path d="M7.5 10.5V17M7.5 7v.01M11.5 17v-6.5M11.5 13.5a2.2 2.2 0 0 1 4.4 0V17" />
    </>
  ),
};

export interface IconProps {
  name: string;
  size?: number;
  stroke?: number;
  style?: CSSProperties;
  className?: string;
}

export function Icon({
  name,
  size = 18,
  stroke = 2,
  style,
  className,
}: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
      className={className}
      aria-hidden="true"
    >
      {paths[name] ?? null}
    </svg>
  );
}
