"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Stat } from "@/components/ui/stat";
import { Reveal, useReveal } from "@/components/ui/reveal";
import { usePortal } from "./portal-context";

const READOUT: [string, string, string][] = [
  ["Pressão de linha", "148 psi", "ok"],
  ["Temp. fluido", "82 °C", "ok"],
  ["Conversor", "stall 2100", "warn"],
  ["Códigos", "P0741", "warn"],
];

export function Hero() {
  const { openSchedule } = usePortal();
  const staggerRef = useReveal<HTMLDivElement>();

  return (
    <section
      className="blueprint"
      style={{
        position: "relative",
        overflow: "hidden",
        paddingTop: 64,
        paddingBottom: 88,
      }}
    >
      <div
        className="glow-amber"
        style={{
          width: 720,
          height: 520,
          top: -180,
          left: "50%",
          transform: "translateX(-30%)",
        }}
      />
      <div className="wrap" style={{ position: "relative", zIndex: 1 }}>
        <div
          className="hero-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "1.05fr 0.95fr",
            gap: 56,
            alignItems: "center",
          }}
        >
          {/* Left */}
          <div data-stagger ref={staggerRef}>
            <div className="flex center gap-3" style={{ marginBottom: 22 }}>
              <Badge variant="amber" icon="spark">
                Especializada em câmbios · Canoas-RS
              </Badge>
            </div>
            <h1
              style={{ fontSize: "3.5rem", lineHeight: 1.03, marginBottom: 20 }}
            >
              Especialista em câmbio{" "}
              <span className="amber">automático e automatizado.</span>
            </h1>
            <p
              style={{
                fontSize: "1.15rem",
                color: "var(--text-muted)",
                maxWidth: 540,
                marginBottom: 30,
                lineHeight: 1.55,
              }}
            >
              A <strong style={{ color: "var(--text)" }}>Rödelcar</strong> é
              referência em Dualogic, PowerShift, iMotion, Easytronic e DSG.
              Diagnóstico de bancada, sem achismo e sem peça trocada à toa.
            </p>
            <div
              className="flex center gap-3"
              style={{ marginBottom: 40, flexWrap: "wrap" }}
            >
              <Button
                variant="primary"
                size="lg"
                icon="whatsapp"
                onClick={openSchedule}
              >
                Falar com a oficina
              </Button>
              <Link href="/#vitrine" className="btn btn-secondary btn-lg">
                Ver cursos
                <Icon name="arrow" size={19} />
              </Link>
            </div>
            <div
              className="flex center gap-6"
              style={{
                paddingTop: 28,
                borderTop: "1px solid var(--border)",
                maxWidth: 520,
                flexWrap: "wrap",
              }}
            >
              <Stat value="+12" label="sistemas dominados" accent />
              <div
                style={{ width: 1, height: 38, background: "var(--border)" }}
              />
              <Stat value="+2.000" label="mecânicos formados" accent />
              <div
                style={{ width: 1, height: 38, background: "var(--border)" }}
              />
              <Stat value="+5.400" label="câmbios reparados" accent />
            </div>
          </div>

          {/* Right — visual: foto da equipe na bancada + floating diagnostic readout */}
          <Reveal style={{ position: "relative" }}>
            <div
              className="thumb"
              style={{ aspectRatio: "4/5", borderRadius: 14 }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/turmas/t1.jpg"
                alt="Equipe Rödelcar na bancada durante a aula prática"
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  display: "block",
                }}
              />
            </div>
            {/* floating diagnostic readout — overlay no canto inferior direito da imagem */}
            <div
              className="card"
              style={{
                position: "absolute",
                bottom: -20,
                right: -16,
                width: 264,
                padding: 16,
                background: "var(--surface-2)",
                boxShadow: "0 24px 60px -24px rgba(0,0,0,.8), var(--glow-soft)",
              }}
            >
              <div className="flex center between" style={{ marginBottom: 12 }}>
                <span
                  className="tag-mono cyan"
                  style={{ display: "flex", alignItems: "center", gap: 6 }}
                >
                  <span
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: 9999,
                      background: "var(--success)",
                      boxShadow: "0 0 8px var(--success)",
                    }}
                  />
                  DIAGNÓSTICO · LIVE
                </span>
                <Icon
                  name="gauge"
                  size={16}
                  style={{ color: "var(--primary)" }}
                />
              </div>
              {READOUT.map(([k, v, s], i) => (
                <div
                  key={i}
                  className="flex center between"
                  style={{
                    padding: "7px 0",
                    borderTop: i ? "1px solid var(--border)" : "none",
                  }}
                >
                  <span className="tag-mono">{k}</span>
                  <span
                    className="mono"
                    style={{
                      fontSize: "0.78rem",
                      color: s === "warn" ? "var(--warning)" : "var(--text)",
                      fontWeight: 600,
                    }}
                  >
                    {v}
                  </span>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
