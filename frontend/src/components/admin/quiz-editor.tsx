"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import {
  excluirQuiz,
  getQuizAdmin,
  salvarQuiz,
  type AdminQuestao,
} from "@/lib/admin-api";

interface Questao {
  enunciado: string;
  alternativas: { texto: string; correta: boolean }[];
}

const QUESTAO_VAZIA: Questao = {
  enunciado: "",
  alternativas: [
    { texto: "", correta: true },
    { texto: "", correta: false },
  ],
};

/** Editor do quiz de um módulo (questões + alternativas, 1 correta por questão). */
export function QuizEditor({
  moduloId,
  moduloTitulo,
  onClose,
  onToast,
}: {
  moduloId: string;
  moduloTitulo: string;
  onClose: () => void;
  onToast: (msg: string) => void;
}) {
  const [titulo, setTitulo] = useState("Prova do módulo");
  const [notaCorte, setNotaCorte] = useState(70);
  const [ativo, setAtivo] = useState(true);
  const [questoes, setQuestoes] = useState<Questao[]>([{ ...QUESTAO_VAZIA }]);
  const [existe, setExiste] = useState(false);
  const [busy, setBusy] = useState(false);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    getQuizAdmin(moduloId)
      .then((q) => {
        if (q) {
          setExiste(true);
          setTitulo(q.titulo);
          setNotaCorte(Math.round(q.nota_corte));
          setAtivo(q.ativo);
          setQuestoes(
            q.questoes.map((qu) => ({
              enunciado: qu.enunciado,
              alternativas: qu.alternativas.map((a) => ({
                texto: a.texto,
                correta: a.correta,
              })),
            })),
          );
        }
      })
      .catch(() => onToast("Falha ao carregar o quiz."))
      .finally(() => setCarregando(false));
  }, [moduloId]);

  const setQ = (i: number, patch: Partial<Questao>) =>
    setQuestoes((qs) =>
      qs.map((q, idx) => (idx === i ? { ...q, ...patch } : q)),
    );

  const setAlt = (qi: number, ai: number, texto: string) =>
    setQ(qi, {
      alternativas: questoes[qi].alternativas.map((a, idx) =>
        idx === ai ? { ...a, texto } : a,
      ),
    });

  const marcarCorreta = (qi: number, ai: number) =>
    setQ(qi, {
      alternativas: questoes[qi].alternativas.map((a, idx) => ({
        ...a,
        correta: idx === ai,
      })),
    });

  const addAlt = (qi: number) =>
    setQ(qi, {
      alternativas: [
        ...questoes[qi].alternativas,
        { texto: "", correta: false },
      ],
    });

  const rmAlt = (qi: number, ai: number) => {
    const alts = questoes[qi].alternativas.filter((_, idx) => idx !== ai);
    if (alts.length < 2) return;
    if (!alts.some((a) => a.correta)) alts[0].correta = true;
    setQ(qi, { alternativas: alts });
  };

  const valido =
    titulo.trim().length >= 2 &&
    questoes.length > 0 &&
    questoes.every(
      (q) =>
        q.enunciado.trim() &&
        q.alternativas.length >= 2 &&
        q.alternativas.every((a) => a.texto.trim()) &&
        q.alternativas.filter((a) => a.correta).length === 1,
    );

  const salvar = async () => {
    setBusy(true);
    try {
      await salvarQuiz(moduloId, {
        titulo: titulo.trim(),
        nota_corte: notaCorte,
        ativo,
        questoes: questoes.map<AdminQuestao>((q) => ({
          enunciado: q.enunciado.trim(),
          alternativas: q.alternativas.map((a) => ({
            texto: a.texto.trim(),
            correta: a.correta,
          })),
        })),
      });
      onToast("Quiz salvo.");
      onClose();
    } catch {
      onToast("Não foi possível salvar o quiz.");
      setBusy(false);
    }
  };

  const remover = async () => {
    if (!window.confirm("Excluir o quiz deste módulo?")) return;
    setBusy(true);
    try {
      await excluirQuiz(moduloId);
      onToast("Quiz excluído.");
      onClose();
    } catch {
      onToast("Não foi possível excluir o quiz.");
      setBusy(false);
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 70,
        background: "rgba(5,7,10,0.8)",
        display: "grid",
        placeItems: "start center",
        padding: 16,
        overflow: "auto",
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 760, width: "100%", padding: 22, margin: "24px 0" }}
      >
        <div
          className="flex center between"
          style={{ marginBottom: 16, gap: 12 }}
        >
          <h3 style={{ fontSize: "1.15rem" }}>Quiz · {moduloTitulo}</h3>
          <button
            onClick={onClose}
            className="btn btn-ghost btn-sm"
            aria-label="Fechar"
          >
            <Icon name="x" size={18} />
          </button>
        </div>

        {carregando ? (
          <span className="tag-mono muted">Carregando…</span>
        ) : (
          <>
            <div
              className="flex center gap-3"
              style={{ flexWrap: "wrap", marginBottom: 16 }}
            >
              <input
                className="input"
                placeholder="Título do quiz"
                value={titulo}
                onChange={(e) => setTitulo(e.target.value)}
                style={{ flex: 1, minWidth: 200 }}
              />
              <label
                className="flex center gap-2"
                style={{ fontSize: "0.9rem" }}
              >
                Nota de corte
                <input
                  className="input"
                  type="number"
                  min={1}
                  max={100}
                  value={notaCorte}
                  onChange={(e) =>
                    setNotaCorte(parseInt(e.target.value, 10) || 0)
                  }
                  style={{ width: 72 }}
                />
                %
              </label>
              <label
                className="flex center gap-2"
                style={{ fontSize: "0.9rem" }}
              >
                <input
                  type="checkbox"
                  checked={ativo}
                  onChange={(e) => setAtivo(e.target.checked)}
                />
                Ativo (exigido p/ o certificado)
              </label>
            </div>

            <div style={{ display: "grid", gap: 14 }}>
              {questoes.map((q, qi) => (
                <div
                  key={qi}
                  className="card"
                  style={{ padding: 14, background: "var(--surface-2)" }}
                >
                  <div
                    className="flex center between"
                    style={{ marginBottom: 8, gap: 8 }}
                  >
                    <span className="tag-mono subtle">Questão {qi + 1}</span>
                    {questoes.length > 1 && (
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() =>
                          setQuestoes((qs) => qs.filter((_, i) => i !== qi))
                        }
                      >
                        <Icon name="x" size={15} /> Remover
                      </button>
                    )}
                  </div>
                  <textarea
                    className="input"
                    rows={2}
                    placeholder="Enunciado da questão"
                    value={q.enunciado}
                    onChange={(e) => setQ(qi, { enunciado: e.target.value })}
                    style={{ marginBottom: 10, resize: "vertical" }}
                  />
                  <div style={{ display: "grid", gap: 6 }}>
                    {q.alternativas.map((a, ai) => (
                      <div key={ai} className="flex center gap-2">
                        <input
                          type="radio"
                          name={`correta-${qi}`}
                          checked={a.correta}
                          onChange={() => marcarCorreta(qi, ai)}
                          title="Marcar como correta"
                        />
                        <input
                          className="input"
                          placeholder={`Alternativa ${ai + 1}`}
                          value={a.texto}
                          onChange={(e) => setAlt(qi, ai, e.target.value)}
                          style={{ flex: 1 }}
                        />
                        {q.alternativas.length > 2 && (
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => rmAlt(qi, ai)}
                            aria-label="Remover alternativa"
                          >
                            <Icon name="x" size={14} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  {q.alternativas.length < 6 && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => addAlt(qi)}
                      style={{ marginTop: 8 }}
                    >
                      + Alternativa
                    </Button>
                  )}
                  <span
                    className="tag-mono subtle"
                    style={{ display: "block", marginTop: 6 }}
                  >
                    Marque o círculo da alternativa correta.
                  </span>
                </div>
              ))}
            </div>

            <Button
              size="sm"
              variant="secondary"
              icon="book"
              onClick={() => setQuestoes((qs) => [...qs, { ...QUESTAO_VAZIA }])}
              style={{ marginTop: 12 }}
            >
              Adicionar questão
            </Button>

            <div
              className="flex center between"
              style={{ marginTop: 20, gap: 10, flexWrap: "wrap" }}
            >
              <div className="flex center gap-2">
                <Button
                  variant="primary"
                  disabled={!valido || busy}
                  onClick={salvar}
                >
                  {busy ? "Salvando…" : "Salvar quiz"}
                </Button>
                <Button variant="ghost" onClick={onClose}>
                  Cancelar
                </Button>
              </div>
              {existe && (
                <Button
                  variant="ghost"
                  icon="x"
                  onClick={remover}
                  disabled={busy}
                >
                  Excluir quiz
                </Button>
              )}
            </div>
            {!valido && (
              <span
                className="tag-mono subtle"
                style={{ display: "block", marginTop: 8 }}
              >
                Cada questão precisa de enunciado, ≥2 alternativas preenchidas e
                exatamente 1 correta.
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}
