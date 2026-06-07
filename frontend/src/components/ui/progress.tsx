"use client";

import { useEffect, useRef } from "react";

export interface ProgressProps {
  value: number;
}

export function Progress({ value }: ProgressProps) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || !el.parentElement) return;
    const parent = el.parentElement;
    let done = false;
    const fill = () => {
      if (!done) {
        done = true;
        el.style.width = value + "%";
      }
    };
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            fill();
            io.unobserve(parent);
          }
        });
      },
      { threshold: 0.3 },
    );
    io.observe(parent);
    const t = setTimeout(fill, 800);
    return () => {
      io.disconnect();
      clearTimeout(t);
    };
  }, [value]);
  return (
    <div className="progress">
      <span ref={ref} />
    </div>
  );
}
