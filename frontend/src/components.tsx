import type { CSSProperties } from "react";
import { initials, numberHue } from "./util";

/** Avatar con un anillo del color del número por el que escribió el cliente. */
export function Avatar({ name, numberId, size = 40 }: { name: string; numberId?: number; size?: number }) {
  const style = {
    "--size": `${size}px`,
    "--hue": numberId === undefined ? 230 : numberHue(numberId),
  } as CSSProperties;
  return (
    <span className="avatar" style={style} aria-hidden="true">
      {initials(name)}
    </span>
  );
}

/** Punto + etiqueta del número, con su color. */
export function NumberTag({ id, label }: { id: number | undefined; label: string }) {
  const style = { "--hue": id === undefined ? 230 : numberHue(id) } as CSSProperties;
  return (
    <span className="numtag" style={style}>
      <i />
      {label}
    </span>
  );
}

export function OrbitMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <circle cx="16" cy="16" r="5" fill="currentColor" />
      <ellipse cx="16" cy="16" rx="14" ry="6" stroke="currentColor" strokeWidth="1.6" transform="rotate(-28 16 16)" opacity=".85" />
      <ellipse cx="16" cy="16" rx="14" ry="6" stroke="currentColor" strokeWidth="1.6" transform="rotate(32 16 16)" opacity=".45" />
    </svg>
  );
}

const paths: Record<string, string> = {
  chat: "M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9l-4 3v-3H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z",
  pipeline: "M4 4h4v16H4zM10 4h4v10h-4zM16 4h4v6h-4z",
  numbers: "M7 3h10a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM10 18h4",
  waha: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c2.6 2.7 3.9 5.7 3.9 9s-1.3 6.3-3.9 9c-2.6-2.7-3.9-5.7-3.9-9S9.4 5.7 12 3z",
  logout: "M10 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h5M15 8l4 4-4 4M19 12H9",
  back: "M15 5l-7 7 7 7",
};

export function Icon({ name }: { name: keyof typeof paths }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={paths[name]} />
    </svg>
  );
}
