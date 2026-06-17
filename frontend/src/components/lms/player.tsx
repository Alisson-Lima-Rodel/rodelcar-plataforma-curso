"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getAula,
  getCursoPlayer,
  getMatriculas,
  salvarProgresso,
  type AulaDetail,
  type PlayerCurso,
  type PlayerModulo,
} from "@/lib/auth-api";
import { lmsHref } from "@/lib/lms-nav";
import { QuizTaker } from "./quiz-taker";
import { SmartPlayer } from "./smart-player";

function ModuleNav({
  modules,
  currentId,
  initialOpen,
  onPick,
  onQuiz,
}: {
  modules: PlayerModulo[];
  currentId: string | null;
  initialOpen: number;
  onPick: (id: string) => void;
  onQuiz: (quizId: string) => void;
}) {
  const [open, setOpen] = useState(initialOpen);
  useEffect(() => setOpen(initialOpen), [initialOpen]);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {modules.map((m, mi) => {
        const isOpen = open === mi;
        const doneCount = m.aulas.filter((a) => a.concluida).length;
        return (
          <div key={m.id} className="acc-item">
            <button
              className="acc-head"
              onClick={() => setOpen(isOpen ? -1 : mi)}
              style={{ padding: "13px 15px" }}
            >
              <span
                className="mono"
                style={{
                  fontSize: "0.78rem",
                  color:
                    doneCount === m.aulas.length && m.aulas.length
                      ? "var(--success)"
                      : "var(--primary)",
                  width: 24,
                }}
              >
                {String(mi + 1).padStart(2, "0")}
              </span>
              <span
                style={{
                  flex: 1,
                  fontWeight: 600,
                  fontSize: "0.92rem",
                  lineHeight: 1.2,
                }}
              >
                {m.titulo}
              </span>
              <span className="tag-mono" style={{ marginRight: 8 }}>
                {doneCount}/{m.aulas.length}
              </span>
              <Icon
                name="chevron"
                size={16}
                style={{
                  color: "var(--text-muted)",
                  transform: isOpen ? "rotate(180deg)" : "none",
                  transition: "transform 220ms",
                }}
              />
            </button>
            <div
              className="acc-body"
              style={{
                maxHeight: isOpen
                  ? (m.aulas.length + (m.quiz ? 1 : 0)) * 56 + 8
                  : 0,
              }}
            >
              <div style={{ padding: "4px 8px 8px" }}>
                {m.aulas.map((a) => {
                  const isCurrent = currentId === a.id;
                  return (
                    <div
                      key={a.id}
                      className={`lesson ${isCurrent ? "current" : ""}`.trim()}
                      onClick={() => onPick(a.id)}
                      style={{ cursor: "pointer" }}
                    >
                      <span
                        className={`lesson-check ${a.concluida ? "done" : ""} ${isCurrent ? "current" : ""}`.trim()}
                      >
                        {a.concluida ? (
                          <Icon name="check" size={13} stroke={3} />
                        ) : (
                          <Icon name="play" size={10} />
                        )}
                      </span>
                      <span
                        style={{
                          flex: 1,
                          fontSize: "0.88rem",
                          fontWeight: isCurrent ? 600 : 400,
                          color: isCurrent
                            ? "var(--text)"
                            : "var(--text-muted)",
                          lineHeight: 1.25,
                        }}
                      >
                        {a.titulo}
                      </span>
                      <span className="tag-mono">{a.duracao_label}</span>
                    </div>
                  );
                })}
                {m.quiz && (
                  <div
                    className="lesson"
                    onClick={() => onQuiz(m.quiz!.id)}
                    style={{ cursor: "pointer" }}
                  >
                    <span
                      className={`lesson-check ${m.quiz.aprovado ? "done" : ""}`.trim()}
                    >
                      {m.quiz.aprovado ? (
                        <Icon name="check" size={13} stroke={3} />
                      ) : (
                        <Icon name="star" size={11} />
                      )}
                    </span>
                    <span
                      style={{
                        flex: 1,
                        fontSize: "0.88rem",
                        fontWeight: 600,
                        color: "var(--text)",
                      }}
                    >
                      {m.quiz.titulo}
                    </span>
                    <span
                      className="tag-mono"
                      style={{
                        color: m.quiz.aprovado
                          ? "var(--success)"
                          : "var(--primary)",
                      }}
                    >
                      {m.quiz.aprovado ? "aprovado" : "fazer"}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Materials({ aula }: { aula: AulaDetail | undefined }) {
  const mats = aula?.materiais ?? [];
  if (!mats.length) {
    return (
      <div
        className="muted"
        style={{ fontSize: "0.92rem", padding: "8px 2px" }}
      >
        Nenhum material de apoio nesta aula.
      </div>
    );
  }
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {mats.map((m) => (
        <div key={m.id} className="material">
          <span className="file-ico">
            <Icon name="file" size={20} />
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: "0.94rem" }}>{m.nome}</div>
            <span className="tag-mono">PDF</span>
          </div>
          <a
            href={m.url_pdf}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-ghost btn-sm"
          >
            <Icon name="download" size={16} /> Baixar
          </a>
        </div>
      ))}
      <div
        className="flex center gap-3"
        style={{
          marginTop: 6,
          padding: "12px 16px",
          borderRadius: 11,
          background: "var(--surface-2)",
          border: "1px solid var(--border)",
        }}
      >
        <Icon name="infinity" size={18} style={{ color: "var(--accent)" }} />
        <span className="muted" style={{ fontSize: "0.88rem" }}>
          Materiais disponíveis para download enquanto durar seu acesso de 1
          ano.
        </span>
      </div>
    </div>
  );
}

function Community() {
  return (
    <div
      className="flex center gap-3"
      style={{
        padding: "18px 20px",
        borderRadius: 12,
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
      }}
    >
      <Icon name="message" size={20} style={{ color: "var(--accent)" }} />
      <span className="muted" style={{ fontSize: "0.92rem" }}>
        Dúvidas e comunidade por aula chegam em breve. Por enquanto, fale com a
        equipe Rödelcar pelos canais de suporte.
      </span>
    </div>
  );
}

function StateMessage({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  const router = useRouter();
  return (
    <div className="content" style={{ maxWidth: 720 }}>
      <button
        className="btn btn-ghost btn-sm"
        style={{ paddingLeft: 0, marginBottom: 18 }}
        onClick={() => router.push(lmsHref("dashboard"))}
      >
        <Icon name="arrowLeft" size={16} /> Painel
      </button>
      <div className="card" style={{ padding: 28, textAlign: "center" }}>
        <h3 style={{ fontSize: "1.15rem", marginBottom: 8 }}>{title}</h3>
        {children}
      </div>
    </div>
  );
}

export function Player() {
  const router = useRouter();
  const qc = useQueryClient();
  const [querySlug, setQuerySlug] = useState<string | null | undefined>(
    undefined,
  );
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [tab, setTab] = useState("materiais");
  const [quizId, setQuizId] = useState<string | null>(null);

  // slug vem de ?slug= ; na falta, usa a primeira matrícula do aluno.
  useEffect(() => {
    setQuerySlug(new URLSearchParams(window.location.search).get("slug"));
  }, []);

  const matQ = useQuery({
    queryKey: ["me", "matriculas"],
    queryFn: getMatriculas,
    enabled: querySlug === null,
  });
  const slug = querySlug || matQ.data?.items?.[0]?.curso.slug || null;

  const playerQ = useQuery<PlayerCurso>({
    queryKey: ["me", "player", slug],
    queryFn: () => getCursoPlayer(slug as string),
    enabled: !!slug,
  });
  const data = playerQ.data;

  const flat = useMemo(
    () =>
      data
        ? data.modulos.flatMap((m, mi) =>
            m.aulas.map((a) => ({ ...a, moduloTitulo: m.titulo, mi })),
          )
        : [],
    [data],
  );

  // aula atual: a selecionada, ou a primeira não concluída, ou a primeira.
  useEffect(() => {
    if (data && flat.length && !flat.some((a) => a.id === currentId)) {
      const firstUndone = flat.find((a) => !a.concluida) ?? flat[0];
      setCurrentId(firstUndone.id);
    }
  }, [data, flat, currentId]);

  const currentLesson = flat.find((a) => a.id === currentId) ?? null;
  const aulaQ = useQuery<AulaDetail>({
    queryKey: ["aula", currentId],
    queryFn: () => getAula(currentId as string),
    enabled: !!currentId,
  });

  const concludeM = useMutation({
    mutationFn: (aulaId: string) => salvarProgresso(aulaId, 100, true),
    onSuccess: async () => {
      const idx = flat.findIndex((a) => a.id === currentId);
      const next = flat[idx + 1];
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["me", "player", slug] }),
        qc.invalidateQueries({ queryKey: ["me", "dashboard"] }),
        qc.invalidateQueries({ queryKey: ["me", "matriculas"] }),
      ]);
      if (next) setCurrentId(next.id);
    },
  });

  // ── Estados de carga / vazio / erro ─────────────────────────────────────────
  if (querySlug === null && matQ.isLoading) {
    return (
      <div className="content">
        <span className="tag-mono muted">Carregando seu curso…</span>
      </div>
    );
  }
  if (!slug) {
    return (
      <StateMessage title="Você ainda não está matriculado em nenhum curso.">
        <Button
          variant="secondary"
          icon="book"
          onClick={() => router.push("/cursos")}
        >
          Ver cursos
        </Button>
      </StateMessage>
    );
  }
  if (playerQ.isLoading) {
    return (
      <div className="content">
        <span className="tag-mono muted">Carregando seu curso…</span>
      </div>
    );
  }
  if (playerQ.isError || !data) {
    return (
      <StateMessage title="Não foi possível abrir este curso.">
        <p className="muted" style={{ fontSize: "0.93rem" }}>
          Sua matrícula pode ter expirado. Volte ao painel e tente novamente.
        </p>
      </StateMessage>
    );
  }

  const doneTotal = flat.filter((a) => a.concluida).length;
  const tabs = [
    { id: "materiais", label: "Materiais", icon: "file" },
    { id: "duvidas", label: "Dúvidas & Comunidade", icon: "message" },
  ];

  return (
    <div className="content" style={{ maxWidth: 1320 }}>
      {/* breadcrumb */}
      <div
        className="flex center between"
        style={{ marginBottom: 18, gap: 12, flexWrap: "wrap" }}
      >
        <button
          className="btn btn-ghost btn-sm"
          style={{ paddingLeft: 0 }}
          onClick={() => router.push(lmsHref("dashboard"))}
        >
          <Icon name="arrowLeft" size={16} /> Painel
        </button>
        <span className="tag-mono">
          {data.curso.titulo}
          {currentLesson ? ` · ${currentLesson.moduloTitulo}` : ""}
        </span>
      </div>

      <div className="player-grid">
        {/* MAIN */}
        <div>
          <SmartPlayer
            videoId={aulaQ.data?.panda_video_id ?? null}
            title={currentLesson?.titulo}
          />

          {/* título + ação dominante */}
          <div
            className="flex between"
            style={{
              alignItems: "flex-start",
              margin: "22px 0 8px",
              gap: 24,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div className="tag-mono amber" style={{ marginBottom: 8 }}>
                {(currentLesson?.moduloTitulo ?? "").toUpperCase()}
              </div>
              <h1 style={{ fontSize: "1.85rem", marginBottom: 6 }}>
                {currentLesson?.titulo ?? "—"}
              </h1>
              <div className="flex center gap-3">
                <Badge icon="clock">
                  {currentLesson?.duracao_label ?? "—"}
                </Badge>
                {currentLesson?.concluida && (
                  <Badge variant="success" icon="check">
                    Concluída
                  </Badge>
                )}
              </div>
            </div>
            {currentLesson &&
              (currentLesson.concluida ? (
                <Button
                  variant="secondary"
                  size="lg"
                  iconRight="arrow"
                  onClick={() => {
                    const idx = flat.findIndex((a) => a.id === currentId);
                    const next = flat[idx + 1];
                    if (next) setCurrentId(next.id);
                  }}
                  style={{ flexShrink: 0 }}
                >
                  Próxima aula
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="lg"
                  icon="check"
                  onClick={() => concludeM.mutate(currentLesson.id)}
                  className={concludeM.isPending ? "is-disabled" : ""}
                  style={{ flexShrink: 0 }}
                >
                  {concludeM.isPending ? "Salvando…" : "Concluir e avançar"}
                </Button>
              ))}
          </div>

          {/* faixa de conclusão do curso */}
          {data.concluido && (
            <div
              className="flex center between"
              style={{
                margin: "18px 0",
                padding: "14px 18px",
                borderRadius: 12,
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                gap: 16,
                flexWrap: "wrap",
              }}
            >
              <div className="flex center gap-3">
                <Icon
                  name="award"
                  size={20}
                  style={{ color: "var(--success)" }}
                />
                <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>
                  Curso concluído — seu certificado está disponível.
                </span>
              </div>
              <Button
                variant="primary"
                size="sm"
                iconRight="arrow"
                onClick={() =>
                  router.push(
                    `${lmsHref("certificate")}?slug=${data.curso.slug}`,
                  )
                }
              >
                Ver certificado
              </Button>
            </div>
          )}

          {/* tabs */}
          <div className="tabs-bar" style={{ marginTop: 24 }}>
            {tabs.map((t) => (
              <button
                key={t.id}
                className={`tab-btn ${tab === t.id ? "active" : ""}`.trim()}
                onClick={() => setTab(t.id)}
              >
                <Icon name={t.icon} size={16} />
                {t.label}
              </button>
            ))}
          </div>

          {tab === "materiais" && <Materials aula={aulaQ.data} />}
          {tab === "duvidas" && <Community />}
        </div>

        {/* SIDEBAR — accordion de módulos */}
        <aside style={{ position: "sticky", top: 92 }}>
          <div className="card" style={{ padding: 16 }}>
            <div
              className="flex center between"
              style={{ marginBottom: 6, padding: "0 4px" }}
            >
              <h4 style={{ fontSize: "0.96rem" }}>Conteúdo do curso</h4>
              <span className="tag-mono">
                {doneTotal}/{flat.length}
              </span>
            </div>
            <div className="progress" style={{ margin: "10px 4px 16px" }}>
              <span style={{ width: `${data.progresso_percentual}%` }} />
            </div>
            <ModuleNav
              modules={data.modulos}
              currentId={currentId}
              initialOpen={currentLesson?.mi ?? 0}
              onPick={setCurrentId}
              onQuiz={setQuizId}
            />
          </div>
        </aside>
      </div>
      {quizId && (
        <QuizTaker
          quizId={quizId}
          onClose={() => setQuizId(null)}
          onPassed={() => {
            qc.invalidateQueries({ queryKey: ["me", "player", slug] });
            qc.invalidateQueries({ queryKey: ["quiz", quizId] });
          }}
        />
      )}
    </div>
  );
}
