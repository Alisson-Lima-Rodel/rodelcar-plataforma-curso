"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/components/providers/auth-provider";
import { getDashboard, getMatriculas } from "@/lib/auth-api";
import { ReferralCard } from "./referral-card";
import { lmsHref } from "@/lib/lms-nav";
import type { Kpi as KpiType } from "@/lib/student-data";
import { Kpi } from "./kpi";

// Capa da aula = thumbnail ESTÁTICA do vídeo no Panda (não o preview animado),
// mesmo CDN do player. Derivada do embed base (NEXT_PUBLIC_PANDA_EMBED_BASE:
// player-vz-XXXX.tv… → cdn/vz-XXXX) + o external_id da aula. Sem env/id, cai no
// placeholder.
const PANDA_BASE = process.env.NEXT_PUBLIC_PANDA_EMBED_BASE ?? "";
function capaAula(externalId?: string | null): string | null {
  if (!externalId || !PANDA_BASE) return null;
  try {
    const host = new URL(PANDA_BASE).host;
    const vz = host.split(".")[0].replace(/^player-/, "");
    return `https://cdn.pandavideo.com/${vz}/${externalId}/thumbnail.jpg`;
  } catch {
    return null;
  }
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

export function Dashboard() {
  const router = useRouter();
  const { aluno } = useAuth();
  const goCurso = (id: string, slug: string) =>
    router.push(`${lmsHref(id)}?slug=${encodeURIComponent(slug)}`);
  const [hello, setHello] = useState("Olá");
  useEffect(() => setHello(greeting()), []);

  const dashQ = useQuery({
    queryKey: ["me", "dashboard"],
    queryFn: getDashboard,
  });
  const matQ = useQuery({
    queryKey: ["me", "matriculas"],
    queryFn: getMatriculas,
  });

  const first = (aluno?.nome ?? "").split(" ")[0] || "aluno";
  const dash = dashQ.data;
  const capa = capaAula(dash?.ultima_aula?.panda_external_id);
  const mats = matQ.data?.items ?? [];
  const progressoMedio = mats.length
    ? Math.round(
        mats.reduce((s, m) => s + m.progresso_percentual, 0) / mats.length,
      )
    : 0;

  const kpis: KpiType[] = dash
    ? [
        {
          label: "Aulas concluídas",
          value: String(dash.resumo.aulas_concluidas),
          sub: "no histórico",
          delta: "progresso real",
          trend: "up",
          icon: "checkCircle",
          spark: [3, 5, 4, 7, 6, 9, 8, 12],
        },
        {
          label: "Cursos ativos",
          value: String(dash.resumo.cursos_ativos),
          sub: "matrículas",
          delta: "em andamento",
          trend: "flat",
          icon: "book",
          spark: [1, 1, 2, 2, 2, 3, 3, 3],
        },
        {
          label: "Certificados",
          value: String(dash.resumo.certificados),
          sub: "emitidos",
          delta: "conclua p/ emitir",
          trend: "flat",
          icon: "award",
          spark: [0, 0, 0, 1, 1, 1, 1, 1],
        },
        {
          label: "Progresso médio",
          value: `${progressoMedio}%`,
          sub: "das trilhas",
          delta: "média dos cursos",
          trend: "up",
          icon: "gauge",
          spark: [2, 3, 4, 5, 6, 7, 8, 9],
        },
      ]
    : [];

  if (dashQ.isLoading || matQ.isLoading) {
    return (
      <div className="content">
        <span className="tag-mono muted">Carregando seu painel…</span>
      </div>
    );
  }

  return (
    <div className="content blueprint" style={{ position: "relative" }}>
      {/* saudação */}
      <Reveal style={{ marginBottom: 26 }}>
        <div className="tag-mono amber" style={{ marginBottom: 8 }}>
          // PAINEL DO ALUNO
        </div>
        <h1 style={{ fontSize: "2.1rem", marginBottom: 6 }}>
          {hello}, {first}.
        </h1>
        <p className="muted">
          {mats.length ? (
            <>
              Você tem{" "}
              <strong style={{ color: "var(--text)" }}>
                {dash?.resumo.cursos_ativos} curso(s)
              </strong>{" "}
              em andamento. Bora continuar?
            </>
          ) : (
            "Você ainda não tem matrículas ativas."
          )}
        </p>
      </Reveal>

      {/* alertas reais de vigência */}
      {dash?.alertas.map((a, i) => (
        <Reveal
          key={i}
          className="alert alert-warning"
          style={{ marginBottom: 24 }}
        >
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
              {a.mensagem}
            </div>
            <span className="muted" style={{ fontSize: "0.9rem" }}>
              Renove para manter o histórico, certificados e a comunidade.
            </span>
          </div>
          <Button variant="secondary" size="sm" iconRight="arrow">
            Renovar acesso
          </Button>
        </Reveal>
      ))}

      {/* retomar última aula (real) */}
      {dash?.ultima_aula && (
        <Reveal className="resume" style={{ marginBottom: 32 }}>
          <div
            className="thumb"
            style={{
              borderRadius: 0,
              border: "none",
              borderRight: "1px solid var(--border)",
              ...(capa
                ? {
                    backgroundImage: `url("${capa}")`,
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                  }
                : {}),
            }}
          >
            <div className="play-btn">
              <Icon name="play" size={22} />
            </div>
            {!capa && <span className="thumb-label">[ aula · 16:9 ]</span>}
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
              <span className="tag-mono">{dash.ultima_aula.curso_slug}</span>
            </div>
            <h2 style={{ fontSize: "1.7rem", marginBottom: 8 }}>
              {dash.ultima_aula.titulo}
            </h2>
            <div style={{ marginBottom: 20, maxWidth: 460 }}>
              <div className="flex between" style={{ marginBottom: 7 }}>
                <span className="tag-mono">
                  {Math.round(dash.ultima_aula.percentual)}% concluído
                </span>
              </div>
              <Progress value={dash.ultima_aula.percentual} />
            </div>
            <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
              <Button
                variant="primary"
                size="lg"
                icon="play"
                onClick={() =>
                  goCurso("player", dash?.ultima_aula?.curso_slug ?? "")
                }
              >
                Retomar aula
              </Button>
            </div>
          </div>
        </Reveal>
      )}

      {/* KPIs (reais) */}
      <div className="flex center between" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "1.2rem" }}>Seu progresso</h3>
        <span className="tag-mono">dados ao vivo</span>
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
        {kpis.map((k, i) => (
          <Kpi key={i} k={k} />
        ))}
      </Reveal>

      {/* trilhas (matrículas reais) */}
      <div className="flex center between" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "1.2rem" }}>Suas trilhas</h3>
      </div>
      {mats.length === 0 ? (
        <div className="card" style={{ padding: 28, textAlign: "center" }}>
          <p style={{ fontWeight: 600, marginBottom: 4 }}>
            Nenhum curso vigente
          </p>
          <p className="muted" style={{ marginBottom: 14 }}>
            Você ainda não tem um curso ativo. Explore o catálogo e comece hoje.
          </p>
          <Button
            variant="primary"
            icon="spark"
            onClick={() => router.push("/catalogo")}
          >
            Ver catálogo
          </Button>
        </div>
      ) : (
        <Reveal
          stagger
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          {mats.map((m) => {
            const complete = m.progresso_percentual >= 100;
            return (
              <div
                key={m.id}
                className="track"
                onClick={() =>
                  m.status !== "ativo"
                    ? router.push(lmsHref("courses"))
                    : goCurso(complete ? "certificate" : "player", m.curso.slug)
                }
              >
                <span
                  className="track-ico"
                  style={{
                    color: complete ? "var(--success)" : "var(--text-muted)",
                  }}
                >
                  <Icon name={complete ? "checkCircle" : "gauge"} size={26} />
                </span>
                <div style={{ minWidth: 0 }}>
                  <div
                    className="flex center gap-3"
                    style={{ marginBottom: 8 }}
                  >
                    <span style={{ fontWeight: 600, fontSize: "1.02rem" }}>
                      {m.curso.titulo}
                    </span>
                    {complete && (
                      <Badge variant="success" icon="check">
                        Concluído
                      </Badge>
                    )}
                    {m.status !== "ativo" && (
                      <Badge variant="warning">{m.status}</Badge>
                    )}
                  </div>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 14 }}
                  >
                    <div
                      className="progress"
                      style={{ flex: 1, maxWidth: 420 }}
                    >
                      <span style={{ width: m.progresso_percentual + "%" }} />
                    </div>
                    <span className="tag-mono" style={{ whiteSpace: "nowrap" }}>
                      {m.dias_restantes} dias restantes
                    </span>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div
                    className="price"
                    style={{
                      fontSize: "1.6rem",
                      color: complete ? "var(--success)" : "var(--primary)",
                    }}
                  >
                    {Math.round(m.progresso_percentual)}%
                  </div>
                  <Icon
                    name="chevronRight"
                    size={18}
                    style={{ color: "var(--text-subtle)" }}
                  />
                </div>
              </div>
            );
          })}
        </Reveal>
      )}

      <div style={{ marginTop: 28 }}>
        <ReferralCard />
      </div>
    </div>
  );
}
