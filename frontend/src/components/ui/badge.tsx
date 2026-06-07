import type { CSSProperties, ReactNode } from "react";
import { Icon } from "./icon";

export interface BadgeProps {
  variant?: "premium" | "amber" | "cyan" | "success" | "warning" | "";
  children?: ReactNode;
  icon?: string;
  style?: CSSProperties;
}

export function Badge({ variant = "", children, icon, style }: BadgeProps) {
  return (
    <span
      className={`badge ${variant ? "badge-" + variant : ""}`.trim()}
      style={style}
    >
      {icon && <Icon name={icon} size={12} />}
      {children}
    </span>
  );
}
