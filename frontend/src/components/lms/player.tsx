"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  PLAYER_MODULES,
  MATERIALS,
  QA,
  type PlayerModule,
} from "@/lib/student-data";
import { lmsHref } from "@/lib/lms-nav";

function ModuleNav({
  modules,
  current,
  onPick,
}: {
  modules: PlayerModule[];
  current: string;
  onPick: (k: string) => void;
}) {
  const [open, setOpen] = useState(2);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {modules.map((m, mi) => {
        const isOpen = open === mi;
        const doneCount = m.lessons.filter((l) => l.state === "done").length;
        return (
          <div key={mi} className="acc-item">
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
                    doneCount === m.lessons.length
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
                {m.t}
              </span>
              <span className="tag-mono" style={{ marginRight: 8 }}>
                {doneCount}/{m.lessons.length}
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
              style={{ maxHeight: isOpen ? m.lessons.length * 56 + 8 : 0 }}
            >
              <div style={{ padding: "4px 8px 8px" }}>
                {m.lessons.map((l, li) => {
                  const key = `${mi}-${li}`;
                  const isCurrent = current === key;
                  return (
                    <div
                      key={li}
                      className={`lesson ${isCurrent ? "current" : ""}`.trim()}
                      onClick={() => l.state !== "locked" && onPick(key)}
                      style={{
                        cursor:
                          l.state === "locked" ? "not-allowed" : "pointer",
                        opacity: l.state === "locked" ? 0.55 : 1,
                      }}
                    >
                      <span
                        className={`lesson-check ${l.state === "done" ? "done" : ""} ${isCurrent ? "current" : ""}`.trim()}
                      >
                        {l.state === "done" ? (
                          <Icon name="check" size={13} stroke={3} />
                        ) : l.state === "locked" ? (
                          <Icon
                            name="lock"
                            size={11}
                            style={{ color: "var(--text-subtle)" }}
                          />
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
                        {l.t}
                      </span>
                      <span className="tag-mono">{l.dur}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Materials() {
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {MATERIALS.map((m, i) => (
        <div key={i} className="material">
          <span className="file-ico">
            <Icon name="file" size={20} />
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: "0.94rem" }}>{m.t}</div>
            <span className="tag-mono">
              {m.type} · {m.size} · {m.pages} pág.
            </span>
          </div>
          <Button variant="ghost" size="sm" icon="download">
            Baixar
          </Button>
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
  const [text, setText] = useState("");
  return (
    <div>
      <div className="flex gap-3" style={{ marginBottom: 8 }}>
        <textarea
          className="textarea"
          placeholder="Tem uma dúvida sobre esta aula? Pergunte à comunidade e à equipe Rödelcar..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          style={{ minHeight: 70 }}
        />
      </div>
      <div className="flex between center" style={{ marginBottom: 4 }}>
        <span className="tag-mono">{QA.length} perguntas nesta aula</span>
        <Button variant="primary" size="sm" icon="message">
          Publicar pergunta
        </Button>
      </div>
      <div>
        {QA.map((q, i) => (
          <div key={i} className="qa">
            <span
              className="avatar"
              style={{
                background: q.instructor ? "var(--primary)" : undefined,
                color: q.instructor ? "var(--primary-fg)" : undefined,
                borderColor: q.instructor ? "var(--primary)" : undefined,
              }}
            >
              {q.initials}
            </span>
            <div>
              <div
                className="flex center gap-3"
                style={{ marginBottom: 5, flexWrap: "wrap" }}
              >
                <span style={{ fontWeight: 600, fontSize: "0.92rem" }}>
                  {q.name}
                </span>
                {q.instructor && (
                  <Badge variant="amber" icon="shield">
                    Instrutor
                  </Badge>
                )}
                <span className="tag-mono subtle">{q.time}</span>
              </div>
              <p
                style={{
                  fontSize: "0.93rem",
                  color: "var(--text-muted)",
                  lineHeight: 1.5,
                  marginBottom: 10,
                }}
              >
                {q.text}
              </p>
              <div className="flex center gap-6">
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ padding: "4px 6px", color: "var(--text-subtle)" }}
                >
                  <Icon name="spark" size={14} /> {q.likes}
                </button>
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ padding: "4px 6px", color: "var(--text-subtle)" }}
                >
                  <Icon name="message" size={14} /> {q.replies} respostas
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Player() {
  const router = useRouter();
  const [current, setCurrent] = useState("2-1");
  const [tab, setTab] = useState("materiais");

  const [mi, li] = current.split("-").map(Number);
  const lesson = {
    ...PLAYER_MODULES[mi].lessons[li],
    module: PLAYER_MODULES[mi].t,
  };

  const tabs = [
    {
      id: "materiais",
      label: "Materiais",
      icon: "file",
      count: MATERIALS.length,
    },
    {
      id: "duvidas",
      label: "Dúvidas & Comunidade",
      icon: "message",
      count: QA.length,
    },
    {
      id: "sobre",
      label: "Sobre a aula",
      icon: "book",
      count: null as number | null,
    },
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
          Câmbio Automático Convencional · {lesson.module}
        </span>
      </div>

      <div className="player-grid">
        {/* MAIN */}
        <div>
          <div className="video-stage">
            <div
              style={{ textAlign: "center", position: "relative", zIndex: 1 }}
            >
              <div
                className="play-btn"
                style={{
                  width: 72,
                  height: 72,
                  background: "var(--primary)",
                  color: "var(--primary-fg)",
                  margin: "0 auto",
                  boxShadow: "var(--glow)",
                }}
              >
                <Icon name="play" size={28} />
              </div>
            </div>
            <div className="video-controls">
              <div className="scrub">
                <span style={{ width: "42%" }} />
              </div>
              <div className="flex center between">
                <div className="flex center gap-3">
                  <Icon name="play" size={16} style={{ color: "#fff" }} />
                  <span
                    className="tag-mono"
                    style={{ color: "rgba(255,255,255,0.8)" }}
                  >
                    10:18 / 24:15
                  </span>
                </div>
                <div className="flex center gap-3">
                  <span
                    className="badge"
                    style={{
                      background: "rgba(0,0,0,0.4)",
                      borderColor: "rgba(255,255,255,0.2)",
                      color: "#fff",
                    }}
                  >
                    1.0x
                  </span>
                  <span
                    className="badge"
                    style={{
                      background: "rgba(0,0,0,0.4)",
                      borderColor: "rgba(255,255,255,0.2)",
                      color: "#fff",
                    }}
                  >
                    1080p
                  </span>
                </div>
              </div>
            </div>
          </div>

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
                AULA 08 · {lesson.module.toUpperCase()}
              </div>
              <h1 style={{ fontSize: "1.85rem", marginBottom: 6 }}>
                {lesson.t}
              </h1>
              <div className="flex center gap-3">
                <Badge icon="clock">{lesson.dur}</Badge>
                <Badge variant="cyan" icon="users">
                  {QA.length} dúvidas
                </Badge>
              </div>
            </div>
            <Button
              variant="primary"
              size="lg"
              icon="check"
              onClick={() => setCurrent("2-2")}
              style={{ flexShrink: 0 }}
            >
              Concluir e avançar
            </Button>
          </div>

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
                {t.count != null && (
                  <span
                    className="tag-mono"
                    style={{ color: "inherit", opacity: 0.6 }}
                  >
                    ({t.count})
                  </span>
                )}
              </button>
            ))}
          </div>

          {tab === "materiais" && <Materials />}
          {tab === "duvidas" && <Community />}
          {tab === "sobre" && (
            <div style={{ maxWidth: 640 }}>
              <p
                style={{
                  color: "var(--text-muted)",
                  lineHeight: 1.65,
                  marginBottom: 18,
                }}
              >
                Nesta aula você vai ver, na prática, quais parâmetros de dados
                em tempo real realmente importam no diagnóstico: pressão, duty
                cycle dos solenoides, temperatura do fluido e rotação de
                entrada/saída. O objetivo é separar o sinal do ruído — olhar só
                o que aponta para a falha real.
              </p>
              <h4 style={{ fontSize: "1rem", marginBottom: 12 }}>
                Você vai praticar
              </h4>
              <ul style={{ listStyle: "none", display: "grid", gap: 10 }}>
                {[
                  "Montar um dashboard de PIDs essenciais no scanner",
                  "Interpretar duty cycle do solenoide EPC",
                  "Correlacionar rotação de entrada e saída para detectar patinação",
                ].map((t, i) => (
                  <li
                    key={i}
                    className="flex gap-3"
                    style={{ alignItems: "flex-start" }}
                  >
                    <Icon
                      name="checkCircle"
                      size={18}
                      style={{
                        color: "var(--primary)",
                        flexShrink: 0,
                        marginTop: 1,
                      }}
                    />
                    <span style={{ fontSize: "0.93rem" }}>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* SIDEBAR — accordion de módulos */}
        <aside style={{ position: "sticky", top: 92 }}>
          <div className="card" style={{ padding: 16 }}>
            <div
              className="flex center between"
              style={{ marginBottom: 6, padding: "0 4px" }}
            >
              <h4 style={{ fontSize: "0.96rem" }}>Conteúdo do curso</h4>
              <span className="tag-mono">8/12</span>
            </div>
            <div className="progress" style={{ margin: "10px 4px 16px" }}>
              <span style={{ width: "67%" }} />
            </div>
            <ModuleNav
              modules={PLAYER_MODULES}
              current={current}
              onPick={setCurrent}
            />
          </div>
        </aside>
      </div>
    </div>
  );
}
