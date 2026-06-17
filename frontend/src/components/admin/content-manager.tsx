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
  enviarVideoPanda,
  excluirAula,
  excluirModulo,
  gerarUploadAula,
  listarConteudo,
  sincronizarAulaPanda,
  type AdminAula,
  type AdminModulo,
  type PandaVideoItem,
} from "@/lib/admin-api";
import { QuizEditor } from "./quiz-editor";
import { RetencaoModal } from "./retencao-modal";
import { PandaPickerModal } from "./panda-picker-modal";

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
  ensureSaved,
  busy,
}: {
  initial?: AdminAula;
  onSave: (data: Record<string, unknown>) => void;
  onCancel: () => void;
  // Garante que a aula exista (cria se nova) e devolve-a — usado pelo upload,
  // que precisa de um id antes de subir o arquivo.
  ensureSaved: (data: Record<string, unknown>) => Promise<AdminAula>;
  busy: boolean;
}) {
  const [titulo, setTitulo] = useState(initial?.titulo ?? "");
  const [panda, setPanda] = useState(initial?.panda_video_id ?? "");
  const [dur, setDur] = useState(
    initial ? durLabel(initial.duracao_segundos) : "",
  );
  const [gratuita, setGratuita] = useState(initial?.gratuita ?? false);
  const [upPct, setUpPct] = useState<number | null>(null);
  const [upErr, setUpErr] = useState<string | null>(null);
  const [showPicker, setShowPicker] = useState(false);

  const aulaId = initial?.id;

  const selecionarDaBiblioteca = (v: PandaVideoItem) => {
    setPanda(v.id);
    if (v.duracao_segundos) setDur(durLabel(v.duracao_segundos));
  };

  const enviarArquivo = async (file: File) => {
    setUpErr(null);
    // Upload exige um id. Se a aula é nova, cria-a primeiro (precisa de título).
    let id = aulaId;
    if (!id) {
      if (!titulo.trim()) {
        setUpErr("Dê um título à aula antes de enviar o vídeo.");
        return;
      }
      try {
        const a = await ensureSaved({
          titulo: titulo.trim(),
          duracao_segundos: parseDur(dur),
          gratuita,
        });
        id = a.id;
      } catch {
        setUpErr("Não foi possível criar a aula para o upload.");
        return;
      }
    }
    setUpPct(0);
    try {
      const info = await gerarUploadAula(id, {
        filename: file.name,
        size: file.size,
        content_type: file.type || undefined,
      });
      await enviarVideoPanda(info.upload_url, file, setUpPct);
      setPanda(info.video_id);
      setUpPct(100);
      // Duração só fica pronta após a conversão; ignora se ainda convertendo.
      try {
        const s = await sincronizarAulaPanda(id);
        if (s.duracao_segundos) setDur(durLabel(s.duracao_segundos));
      } catch {
        /* convertendo ainda — admin sincroniza depois */
      }
    } catch (e) {
      setUpErr(e instanceof Error ? e.message : "Falha no upload");
      setUpPct(null);
    }
  };

  const sincronizar = async () => {
    if (!aulaId) return;
    setUpErr(null);
    try {
      const s = await sincronizarAulaPanda(aulaId);
      if (s.duracao_segundos) setDur(durLabel(s.duracao_segundos));
    } catch (e) {
      setUpErr(e instanceof Error ? e.message : "Falha ao sincronizar");
    }
  };

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
      <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => setShowPicker(true)}
        >
          <Icon name="play" size={14} /> Selecionar do Panda
        </button>
        <label
          className="btn btn-ghost btn-sm"
          style={{
            cursor: upPct !== null && upPct < 100 ? "wait" : "pointer",
          }}
        >
          <Icon name="file" size={15} /> Enviar vídeo
          <input
            type="file"
            accept="video/*"
            style={{ display: "none" }}
            disabled={upPct !== null && upPct < 100}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) enviarArquivo(f);
            }}
          />
        </label>
        {aulaId && panda && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={sincronizar}
          >
            <Icon name="clock" size={14} /> Sincronizar duração
          </button>
        )}
        {upPct !== null && (
          <span className="tag-mono">
            {upPct < 100
              ? `enviando ${upPct}%`
              : "enviado ✓ (convertendo no Panda)"}
          </span>
        )}
        {upErr && (
          <span className="tag-mono" style={{ color: "var(--primary)" }}>
            {upErr}
          </span>
        )}
      </div>
      {showPicker && (
        <PandaPickerModal
          onSelect={selecionarDaBiblioteca}
          onClose={() => setShowPicker(false)}
        />
      )}
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
  const [quizModulo, setQuizModulo] = useState<{
    id: string;
    titulo: string;
  } | null>(null);
  const [retAula, setRetAula] = useState<AdminAula | null>(null);

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

  // Garante uma aula persistida (sem fechar o form) p/ o upload ter um id. Se já
  // existe, devolve-a; senão cria, passa o form para modo edição e recarrega a
  // lista ao fundo. Sem `key` no <AulaForm>, ele NÃO remonta — preserva o que foi
  // digitado e passa a enxergar o id novo.
  const ensureAula = async (
    data: Record<string, unknown>,
  ): Promise<AdminAula> => {
    if (!aulaForm) throw new Error("sem form de aula");
    if (aulaForm.aula) return aulaForm.aula;
    const created = await criarAula(aulaForm.moduloId, data);
    setAulaForm({ moduloId: aulaForm.moduloId, aula: created });
    reload();
    return created;
  };

  return (
    <div
      className="content blueprint"
      style={{ maxWidth: 980, position: "relative" }}
    >
      {quizModulo && (
        <QuizEditor
          moduloId={quizModulo.id}
          moduloTitulo={quizModulo.titulo}
          onClose={() => setQuizModulo(null)}
          onToast={onToast}
        />
      )}
      {retAula && (
        <RetencaoModal
          aulaId={retAula.id}
          titulo={retAula.titulo}
          onClose={() => setRetAula(null)}
        />
      )}
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
                  icon="star"
                  onClick={() => setQuizModulo({ id: m.id, titulo: m.titulo })}
                  disabled={busy}
                >
                  Quiz
                </Button>
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
                    {a.panda_video_id && (
                      <Button
                        size="sm"
                        variant="ghost"
                        icon="bolt"
                        onClick={() => setRetAula(a)}
                        disabled={busy}
                      >
                        Retenção
                      </Button>
                    )}
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
                  ensureSaved={ensureAula}
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
