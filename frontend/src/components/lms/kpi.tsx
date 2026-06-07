"use client";

import { useEffect, useRef } from "react";
import { Icon } from "@/components/ui/icon";
import type { Kpi as KpiType } from "@/lib/student-data";

export function Kpi({ k }: { k: KpiType }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) {
            const max = Math.max(...k.spark, 1);
            el.querySelectorAll<HTMLElement>(".spark > span").forEach(
              (bar, i) => {
                setTimeout(() => {
                  bar.style.height = (k.spark[i] / max) * 100 + "%";
                }, i * 50);
              },
            );
            io.unobserve(el);
          }
        }),
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [k.spark]);

  return (
    <div className="kpi" ref={ref}>
      <div className="kpi-label">
        <Icon name={k.icon} size={15} style={{ color: "var(--primary)" }} />
        {k.label}
      </div>
      <div className="flex between" style={{ alignItems: "flex-end" }}>
        <div>
          <div className="kpi-value">
            {k.value}{" "}
            <span
              style={{
                fontSize: "0.9rem",
                fontWeight: 500,
                color: "var(--text-subtle)",
                fontFamily: "var(--font-body)",
              }}
            >
              {k.sub}
            </span>
          </div>
          <span className={`kpi-delta ${k.trend}`}>
            {k.trend === "up" && (
              <Icon
                name="arrow"
                size={11}
                style={{ transform: "rotate(-45deg)" }}
              />
            )}
            {k.delta}
          </span>
        </div>
        <div className="spark" style={{ width: 88 }}>
          {k.spark.map((_, i) => (
            <span
              key={i}
              className={i === k.spark.length - 1 ? "hot" : ""}
              style={{ height: 4 }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
