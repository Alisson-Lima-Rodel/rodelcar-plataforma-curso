"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ADMIN_CRUD,
  atualizarAula,
  atualizarModulo,
  criarAula,
  criarModulo,
  excluirAula,
  excluirModulo,
  listarConteudo,
  type AdminAula,
  type AdminModulo,
} from "@/lib/admin-api";

function durLabel(seg: number): string {
  const m = Math.floor(seg / 60);
  const s = seg % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function parseDur(txt: string): number {
  const [m, s] = txt.split(":").map((x) => parseInt(x, 10) || 0);
  return (m || 0) * 60 + (s || 0);
}

/** Formulário inline de aula (criar/editar). */
function AulaForm({
  initial,
  onSave,
  onCancel,
  busy,
}: {
  initial?: AdminAula;
  onSave: (data: Record<string, unknown>) => void;
  onCancel: () => void;
  busy: boolean;
}) {
  const [titulo, setTitulo] = useState(initial?.titulo ?? "");
  const [panda, setPanda] = useState(initial?.panda_video_id ?? "");
  const [dur, setDur] = useState(
    initial ? durLabel(initial.duracao_segundos) : "",
  );
  const [gratuita, setGratuita] = useState(initial?.gratuita ?? false);

  return (
    <div
      className="card"
      style={{ padding: "12px 14px", marginTop: 8, display: "grid", gap: 8 }}
    >
      <input
        className="input"
        placeholder="Título da aula"
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
      />
      <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
        <input
          className="input"
          placeholder="ID do vídeo (Panda)"
          value={panda}
          onChange={(e) => setPanda(e.target.value)}
          style={{ flex: 1, minWidth: 160 }}
        />
        <input
          className="input"
          placeholder="mm:ss"
          value={dur}
          onChange={(e) => setDur(e.target.value)}
          style={{ width: 90 }}
        />
        <label className="flex center gap-2" style={{ fontSize: "0.9rem" }}>
          <input
            type="checkbox"
            checked={gratuita}
            onChange={(e) => setGratuita(e.target.checked)}
          />
          Aula grátis (preview)
        </label>
      </div>
      <div className="flex center gap-2">
        <Button
          size="sm"
          variant="primary"
          disabled={!titulo.trim() || busy}
          onClick={() =>
            onSave({
              titulo: titulo.trim(),
              panda_video_id: panda.trim() || null,
              duracao_segundos: parseDur(dur),
              gratuita,
            })
          }
        >
          Salvar
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

export function AdminContent({ onToast }: { onToast: (msg: string) => void }) {
  const [cursos, setCursos] = useState<{ id: string; titulo: string }[]>([]);
  const [cursoId, setCursoId] = useState("");
  const [modulos, setModulos] = useState<AdminModulo[] | null>(null);
  const [busy, setBusy] = useState(false);
  // form de aula aberto: { moduloId, aula? }
  const [aulaForm, setAulaForm] = useState<{
    moduloId: string;
    aula?: AdminAula;
  } | null>(null);

  useEffect(() => {
    ADMIN_CRUD.courses
      .list()
      .then((rows) => {
        const cs = rows.map((r) => ({
          id: String(r.id),
          titulo: String(r.titulo),
        }));
        setCursos(cs);
        if (cs[0]) setCursoId(cs[0].id);
      })
      .catch(() => onToast("Falha ao carregar cursos."));
  }, []);

  const carregar = async (id: string) => {
    if (!id) return;
    setModulos(null);
    try {
      setModulos(await listarConteudo(id));
    } catch {
      onToast("Falha ao carregar o conteúdo.");
    }
  };
  useEffect(() => {
    if (cursoId) carregar(cursoId);
  }, [cursoId]);

  const reload = () => carregar(cursoId);
  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true);
    try {
      await fn();
      if (ok) onToast(ok);
      await reload();
    } catch {
      onToast("Não foi possível concluir a ação.");
    } finally {
      setBusy(false);
    }
  };

  const addModulo = () => {
    const titulo = window.prompt("Título do novo módulo:");
    if (!titulo?.trim()) return;
    run(
      () =>
        criarModulo(cursoId, {
          titulo: titulo.trim(),
          ordem: (modulos?.length ?? 0) + 1,
        }),
      "Módulo criado.",
    );
  };
  const renameModulo = (m: AdminModulo) => {
    const titulo = window.prompt("Novo título do módulo:", m.titulo);
    if (!titulo?.trim() || titulo === m.titulo) return;
    run(() => atualizarModulo(m.id, { titulo: titulo.trim() }));
  };
  const delModulo = (m: AdminModulo) => {
    if (
      !window.confirm(
        `Excluir o módulo "${m.titulo}" e suas ${m.aulas.length} aula(s)?`,
      )
    )
      return;
    run(() => excluirModulo(m.id), "Módulo excluído.");
  };
  const delAula = (a: AdminAula) => {
    if (!window.confirm(`Excluir a aula "${a.titulo}"?`)) return;
    run(() => excluirAula(a.id), "Aula excluída.");
  };
  const toggleGratis = (a: AdminAula) =>
    run(() => atualizarAula(a.id, { gratuita: !a.gratuita }));

  const salvarAula = (data: Record<string, unknown>) => {
    if (!aulaForm) return;
    const acao = aulaForm.aula
      ? atualizarAula(aulaForm.aula.id, data)
      : criarAula(aulaForm.moduloId, data);
    run(() => acao, aulaForm.aula ? "Aula atualizada." : "Aula criada.").then(
      () => setAulaForm(null),
    );
  };

  return (
    <div
      className="content blueprint"
      style={{ maxWidth: 980, position: "relative" }}
    >
      <div
        className="flex center gap-3"
        style={{ marginBottom: 20, flexWrap: "wrap" }}
      >
        <span className="tag-mono">Curso:</span>
        <select
          className="input"
          value={cursoId}
          onChange={(e) => setCursoId(e.target.value)}
          style={{ maxWidth: 360 }}
        >
          {cursos.map((c) => (
            <option key={c.id} value={c.id}>
              {c.titulo}
            </option>
          ))}
        </select>
        <div style={{ flex: 1 }} />
        <Button
          variant="primary"
          size="sm"
          icon="book"
          onClick={addModulo}
          disabled={!cursoId || busy}
        >
          Novo módulo
        </Button>
      </div>

      {modulos === null ? (
        <span className="tag-mono muted">Carregando conteúdo…</span>
      ) : modulos.length === 0 ? (
        <div className="card" style={{ padding: 22 }}>
          <span className="muted">
            Este curso ainda não tem módulos. Crie o primeiro acima.
          </span>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {modulos.map((m) => (
            <div key={m.id} className="card" style={{ padding: "14px 18px" }}>
              <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
                <span style={{ fontWeight: 600, flex: 1, minWidth: 180 }}>
                  {m.titulo}
                </span>
                <span className="tag-mono subtle">
                  {m.aulas.length} aula(s)
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  icon="file"
                  onClick={() => renameModulo(m)}
                  disabled={busy}
                >
                  Renomear
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  icon="x"
                  onClick={() => delModulo(m)}
                  disabled={busy}
                >
                  Excluir
                </Button>
              </div>

              <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
                {m.aulas.map((a) => (
                  <div
                    key={a.id}
                    className="flex center gap-3"
                    style={{
                      flexWrap: "wrap",
                      padding: "8px 10px",
                      borderRadius: 8,
                      background: "var(--surface-2)",
                    }}
                  >
                    <Icon
                      name="play"
                      size={14}
                      style={{ color: "var(--text-muted)" }}
                    />
                    <span
                      style={{ flex: 1, minWidth: 160, fontSize: "0.93rem" }}
                    >
                      {a.titulo}
                    </span>
                    <span className="tag-mono subtle">
                      {durLabel(a.duracao_segundos)}
                    </span>
                    {a.gratuita && <Badge variant="success">grátis</Badge>}
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={a.gratuita ? "lock" : "bolt"}
                      onClick={() => toggleGratis(a)}
                      disabled={busy}
                    >
                      {a.gratuita ? "Tornar paga" : "Liberar grátis"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon="file"
                      onClick={() => setAulaForm({ moduloId: m.id, aula: a })}
                      disabled={busy}
                    >
                      Editar
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon="x"
                      onClick={() => delAula(a)}
                      disabled={busy}
                    >
                      Excluir
                    </Button>
                  </div>
                ))}
              </div>

              {aulaForm?.moduloId === m.id ? (
                <AulaForm
                  initial={aulaForm.aula}
                  busy={busy}
                  onSave={salvarAula}
                  onCancel={() => setAulaForm(null)}
                />
              ) : (
                <Button
                  size="sm"
                  variant="secondary"
                  icon="play"
                  style={{ marginTop: 10 }}
                  onClick={() => setAulaForm({ moduloId: m.id })}
                  disabled={busy}
                >
                  Adicionar aula
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
