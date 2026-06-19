"use client";

import { useRef, useState } from "react";
import type { MetricaDiaria } from "@/lib/admin-api";

// Gráfico de linhas em SVG puro (sem dependência): 3 séries sobre N dias.
const W = 920;
const H = 300;
const PAD = { top: 16, right: 16, bottom: 28, left: 36 };

type SerieKey = "acessos" | "aulas_assistidas" | "compras";

const SERIES: { key: SerieKey; label: string; color: string }[] = [
  { key: "acessos", label: "Acessos", color: "var(--primary)" },
  { key: "aulas_assistidas", label: "Aulas assistidas", color: "#38bdf8" },
  { key: "compras", label: "Compras", color: "var(--success)" },
];

function fmtDia(iso: string): string {
  // iso = "YYYY-MM-DD" → "DD/MM"
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

export function MetricsChart({ data }: { data: MetricaDiaria[] }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);

  const n = data.length;
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const maxVal = Math.max(
    1,
    ...data.flatMap((d) => [d.acessos, d.aulas_assistidas, d.compras]),
  );

  const x = (i: number) => PAD.left + (n <= 1 ? 0 : (i / (n - 1)) * plotW);
  const y = (v: number) => PAD.top + plotH - (v / maxVal) * plotH;

  const pathFor = (key: SerieKey) =>
    data
      .map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`)
      .join(" ");

  // Ticks do eixo Y (0, meio, topo) e rótulos de data espaçados.
  const yTicks = [0, Math.round(maxVal / 2), maxVal];
  const xTickEvery = Math.max(1, Math.floor(n / 8));

  const onMove = (e: React.MouseEvent) => {
    const svg = svgRef.current;
    if (!svg || n === 0) return;
    const rect = svg.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - PAD.left) / plotW) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, i)));
  };

  const empty = data.every(
    (d) => d.acessos === 0 && d.aulas_assistidas === 0 && d.compras === 0,
  );

  return (
    <div className="card" style={{ padding: 20 }}>
      <div
        className="flex center between"
        style={{ marginBottom: 12, flexWrap: "wrap", gap: 10 }}
      >
        <div>
          <h3 style={{ fontSize: "1.05rem" }}>Atividade na plataforma</h3>
          <span className="tag-mono subtle">últimos {n} dias</span>
        </div>
        <div className="flex center gap-6" style={{ flexWrap: "wrap" }}>
          {SERIES.map((s) => (
            <span key={s.key} className="flex center gap-3" style={{ fontSize: "0.85rem" }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background: s.color,
                  display: "inline-block",
                }}
              />
              {s.label}
            </span>
          ))}
        </div>
      </div>

      <div style={{ position: "relative", width: "100%" }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          style={{ display: "block", overflow: "visible" }}
          onMouseMove={onMove}
          onMouseLeave={() => setHover(null)}
        >
          {/* grid + rótulos Y */}
          {yTicks.map((t) => (
            <g key={t}>
              <line
                x1={PAD.left}
                x2={W - PAD.right}
                y1={y(t)}
                y2={y(t)}
                stroke="var(--border)"
                strokeWidth={1}
              />
              <text
                x={PAD.left - 8}
                y={y(t) + 4}
                textAnchor="end"
                fontSize={11}
                fill="var(--text-muted)"
                fontFamily="var(--font-mono)"
              >
                {t}
              </text>
            </g>
          ))}

          {/* rótulos X (datas) */}
          {data.map((d, i) =>
            i % xTickEvery === 0 || i === n - 1 ? (
              <text
                key={d.dia}
                x={x(i)}
                y={H - 8}
                textAnchor="middle"
                fontSize={11}
                fill="var(--text-muted)"
                fontFamily="var(--font-mono)"
              >
                {fmtDia(d.dia)}
              </text>
            ) : null,
          )}

          {/* séries */}
          {SERIES.map((s) => (
            <path
              key={s.key}
              d={pathFor(s.key)}
              fill="none"
              stroke={s.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}

          {/* hover: linha vertical + pontos */}
          {hover !== null && (
            <g>
              <line
                x1={x(hover)}
                x2={x(hover)}
                y1={PAD.top}
                y2={PAD.top + plotH}
                stroke="var(--text-muted)"
                strokeDasharray="3 3"
                strokeWidth={1}
              />
              {SERIES.map((s) => (
                <circle
                  key={s.key}
                  cx={x(hover)}
                  cy={y(data[hover][s.key])}
                  r={3.5}
                  fill={s.color}
                />
              ))}
            </g>
          )}
        </svg>

        {hover !== null && (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: `${(x(hover) / W) * 100}%`,
              transform: "translateX(-50%)",
              pointerEvents: "none",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "8px 10px",
              fontSize: "0.8rem",
              whiteSpace: "nowrap",
              boxShadow: "0 6px 18px rgba(0,0,0,0.25)",
            }}
          >
            <div className="tag-mono" style={{ marginBottom: 4 }}>
              {fmtDia(data[hover].dia)}
            </div>
            {SERIES.map((s) => (
              <div key={s.key} className="flex center gap-3">
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 2,
                    background: s.color,
                    display: "inline-block",
                  }}
                />
                {s.label}: <strong>{data[hover][s.key]}</strong>
              </div>
            ))}
          </div>
        )}
      </div>

      {empty && (
        <p className="tag-mono subtle" style={{ marginTop: 10 }}>
          Sem dados no período ainda. Acessos e aulas começam a contar a partir de
          agora; compras refletem o histórico.
        </p>
      )}
    </div>
  );
}
