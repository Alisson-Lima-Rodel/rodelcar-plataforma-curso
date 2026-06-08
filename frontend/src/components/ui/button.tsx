"use client";

import type { CSSProperties, MouseEventHandler, ReactNode } from "react";
import { Icon } from "./icon";

export interface ButtonProps {
  variant?: "primary" | "secondary" | "ghost" | "link";
  size?: "lg" | "sm";
  block?: boolean;
  children?: ReactNode;
  icon?: string;
  iconRight?: string;
  onClick?: MouseEventHandler<HTMLButtonElement | HTMLAnchorElement>;
  href?: string;
  type?: "button" | "submit" | "reset";
  className?: string;
  style?: CSSProperties;
  disabled?: boolean;
  "aria-label"?: string;
}

export function Button({
  variant = "primary",
  size,
  block,
  children,
  icon,
  iconRight,
  onClick,
  href,
  type,
  className = "",
  style,
  disabled,
  ...rest
}: ButtonProps) {
  const cls =
    `btn btn-${variant} ${size ? "btn-" + size : ""} ${block ? "btn-block" : ""} ${className}`.trim();
  const iconSize = size === "lg" ? 19 : 17;
  const inner = (
    <>
      {icon && <Icon name={icon} size={iconSize} />}
      {children}
      {iconRight && <Icon name={iconRight} size={iconSize} />}
    </>
  );
  if (href) {
    const isExternal = href.startsWith("http");
    return (
      <a
        href={href}
        className={cls}
        onClick={onClick}
        style={style}
        {...(isExternal
          ? { target: "_blank", rel: "noopener noreferrer" }
          : {})}
        {...rest}
      >
        {inner}
      </a>
    );
  }
  return (
    <button
      type={type ?? "button"}
      className={cls}
      onClick={onClick}
      style={style}
      disabled={disabled}
      {...rest}
    >
      {inner}
    </button>
  );
}
