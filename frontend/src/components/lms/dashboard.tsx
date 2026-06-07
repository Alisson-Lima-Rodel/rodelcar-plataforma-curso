"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { Progress } from "@/components/ui/progress";
import { STUDENT, KPIS, TRACKS, RESUME } from "@/lib/student-data";
import { lmsHref } from "@/lib/lms-nav";
import { Kpi } from "./kpi";

function computeGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

export function Dashboard() {
  const router = useRouter();
  const nav = (id: string) => router.push(lmsHref(id));
  // Evita mismatch de hidratação (fuso servidor x cliente): saudação só no cliente.
  const [hello, setHello] = useState("Olá");
  useEffect(() => setHello(computeGreeting()), []);

  return (
    <div className="content blueprint" style={{ position: "relative" }}>
      {/* greeting */}
      <Reveal style={{ marginBottom: 26 }}>
        <div className="tag-mono amber" style={{ marginBottom: 8 }}>
          // PAINEL DO ALUNO
        </div>
        <h1 style={{ fontSize: "2.1rem", marginBottom: 6 }}>
          {hello}, {STUDENT.first}.
        </h1>
        <p className="muted">
          Você está a 4 aulas de concluir o{" "}
          <strong style={{ color: "var(--text)" }}>
            Câmbio Automático Convencional
          </strong>
          . Bora fechar?
        </p>
      </Reveal>

      {/* vigência alert (warning, ação secundária) */}
      <Reveal className="alert alert-warning" style={{ marginBottom: 24 }}>
        <span
          className="alert-icon"
          style={{
            background: "rgba(245,158,11,0.14)",
            border: "1px solid rgba(245,158,11,0.4)",
          }}
        >
          <Icon name="clock" size={20} style={{ color: "var(--warning)" }} />
        </span>
        <div style={{ flex: 1 }}>
          <div
            style={{ fontWeight: 600, fontSize: "0.98rem", marginBottom: 2 }}
          >
            Seu acesso Premium expira em {STUDENT.daysLeft} dias
          </div>
          <span className="muted" style={{ fontSize: "0.9rem" }}>
            Renove até {STUDENT.expires} para manter o histórico, certificados e
            a comunidade.
          </span>
        </div>
        <Button variant="secondary" size="sm" iconRight="arrow">
          Renovar acesso
        </Button>
      </Reveal>

      {/* resume card — ação âmbar DOMINANTE */}
      <Reveal className="resume" style={{ marginBottom: 32 }}>
        <div
          className="thumb"
          style={{
            borderRadius: 0,
            border: "none",
            borderRight: "1px solid var(--border)",
          }}
        >
          <div className="play-btn">
            <Icon name="play" size={22} />
          </div>
          <span className="thumb-label">[ aula · 16:9 ]</span>
          <span
            className="badge"
            style={{
              position: "absolute",
              top: 12,
              left: 12,
              background: "rgba(10,12,16,0.8)",
            }}
          >
            {RESUME.time}
          </span>
        </div>
        <div
          style={{
            padding: "26px 30px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          <div
            className="flex center gap-3"
            style={{ marginBottom: 12, flexWrap: "wrap" }}
          >
            <Badge variant="amber" icon="play">
              Retomar de onde parou
            </Badge>
            <span className="tag-mono">{RESUME.module}</span>
          </div>
          <h2 style={{ fontSize: "1.7rem", marginBottom: 8 }}>
            {RESUME.lesson}
          </h2>
          <p
            className="muted"
            style={{ fontSize: "0.95rem", marginBottom: 18 }}
          >
            {RESUME.course}
          </p>
          <div style={{ marginBottom: 20, maxWidth: 460 }}>
            <div className="flex between" style={{ marginBottom: 7 }}>
              <span className="tag-mono">{RESUME.pct}% concluído</span>
              <span className="tag-mono subtle">{RESUME.left}</span>
            </div>
            <Progress value={RESUME.pct} />
          </div>
          <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
            <Button
              variant="primary"
              size="lg"
              icon="play"
              onClick={() => nav("player")}
            >
              Retomar aula
            </Button>
            <Button variant="ghost" onClick={() => nav("courses")}>
              Ver o curso
            </Button>
          </div>
        </div>
      </Reveal>

      {/* KPIs (Tremor) */}
      <div className="flex center between" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "1.2rem" }}>Seu progresso</h3>
        <span className="tag-mono">últimos 8 dias</span>
      </div>
      <Reveal
        stagger
        className="kpi-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: 18,
          marginBottom: 36,
        }}
      >
        {KPIS.map((k, i) => (
          <Kpi key={i} k={k} />
        ))}
      </Reveal>

      {/* Trilhas */}
      <div className="flex center between" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "1.2rem" }}>Suas trilhas</h3>
        <Button variant="link" iconRight="arrow" onClick={() => nav("courses")}>
          Ver todas
        </Button>
      </div>
      <Reveal
        stagger
        style={{ display: "flex", flexDirection: "column", gap: 12 }}
      >
        {TRACKS.map((t) => (
          <div
            key={t.id}
            className="track"
            onClick={() => nav(t.complete ? "certificate" : "player")}
          >
            <span
              className="track-ico"
              style={{
                color: t.complete ? "var(--success)" : "var(--text-muted)",
              }}
            >
              <Icon name={t.complete ? "checkCircle" : t.icon} size={26} />
            </span>
            <div style={{ minWidth: 0 }}>
              <div className="flex center gap-3" style={{ marginBottom: 8 }}>
                <span style={{ fontWeight: 600, fontSize: "1.02rem" }}>
                  {t.title}
                </span>
                {t.complete && (
                  <Badge variant="success" icon="check">
                    Concluído
                  </Badge>
                )}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <div className="progress" style={{ flex: 1, maxWidth: 420 }}>
                  <span style={{ width: t.pct + "%" }} />
                </div>
                <span className="tag-mono" style={{ whiteSpace: "nowrap" }}>
                  {t.done}/{t.total} aulas
                </span>
              </div>
              {!t.complete && (
                <span
                  className="tag-mono subtle"
                  style={{ display: "block", marginTop: 8 }}
                >
                  Próxima: {t.next}
                </span>
              )}
            </div>
            <div style={{ textAlign: "right" }}>
              <div
                className="price"
                style={{
                  fontSize: "1.6rem",
                  color: t.complete ? "var(--success)" : "var(--primary)",
                }}
              >
                {t.pct}%
              </div>
              {t.complete ? (
                <span className="tag-mono cyan">ver certificado</span>
              ) : (
                <Icon
                  name="chevronRight"
                  size={18}
                  style={{ color: "var(--text-subtle)" }}
                />
              )}
            </div>
          </div>
        ))}
      </Reveal>
    </div>
  );
}
