"use client";

import { useEffect, useRef } from "react";
import type { CSSProperties, ElementType, ReactNode } from "react";

/** Revela o elemento ao entrar na viewport, com trava de segurança caso a
 *  transição fique presa (timeline pausada / iframe inativo). */
export function useReveal<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!window.matchMedia("(prefers-reduced-motion: no-preference)").matches) {
      el.classList.add("in", "anim-done");
      return;
    }
    let done = false;
    let lockT: ReturnType<typeof setTimeout> | undefined;
    const reveal = () => {
      if (done) return;
      done = true;
      el.classList.add("in");
      lockT = setTimeout(() => el.classList.add("anim-done"), 900);
    };
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            reveal();
            io.unobserve(el);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    const t = setTimeout(reveal, 700);
    return () => {
      io.disconnect();
      clearTimeout(t);
      if (lockT) clearTimeout(lockT);
    };
  }, []);
  return ref;
}

export interface RevealProps {
  children: ReactNode;
  className?: string;
  stagger?: boolean;
  as?: ElementType;
  style?: CSSProperties;
}

export function Reveal({
  children,
  className = "",
  stagger,
  as = "div",
  style,
}: RevealProps) {
  const ref = useReveal<HTMLElement>();
  const Tag = as as ElementType;
  const props: Record<string, unknown> = {
    ref,
    className: `${stagger ? "" : "reveal"} ${className}`.trim(),
    style,
  };
  if (stagger) props["data-stagger"] = true;
  return <Tag {...props}>{children}</Tag>;
}
