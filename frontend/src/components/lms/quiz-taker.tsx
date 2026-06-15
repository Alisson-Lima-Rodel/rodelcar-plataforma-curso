"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { getQuiz, responderQuiz, type QuizResultado } from "@/lib/auth-api";

/** Modal de quiz do aluno: responde, corrige no servidor e mostra o resultado. */
export function QuizTaker({
  quizId,
  onClose,
  onPassed,
}: {
  quizId: string;
  onClose: () => void;
  onPassed: () => void;
}) {
  const quizQ = useQuery({
    queryKey: ["quiz", quizId],
    queryFn: () => getQuiz(quizId),
  });
  const [respostas, setRespostas] = useState<Record<string, string>>({});
  const [resultado, setResultado] = useState<QuizResultado | null>(null);

  const enviar = useMutation({
    mutationFn: () =>
      responderQuiz(
        quizId,
        Object.entries(respostas).map(([questao_id, alternativa_id]) => ({
          questao_id,
          alternativa_id,
        })),
      ),
    onSuccess: (r) => {
      setResultado(r);
      if (r.aprovado) onPassed();
    },
  });

  const quiz = quizQ.data;
  const todas = quiz && quiz.questoes.every((q) => respostas[q.id]);

  const refazer = () => {
    setRespostas({});
    setResultado(null);
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 70,
        background: "rgba(5,7,10,0.82)",
        display: "grid",
        placeItems: "start center",
        padding: 16,
        overflow: "auto",
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 680, width: "100%", padding: 24, margin: "24px 0" }}
      >
        <div
          className="flex center between"
          style={{ marginBottom: 14, gap: 12 }}
        >
          <span className="flex center gap-2" style={{ fontWeight: 600 }}>
            <Icon name="star" size={17} style={{ color: "var(--primary)" }} />
            {quiz?.titulo ?? "Quiz"}
          </span>
          <button
            onClick={onClose}
            className="btn btn-ghost btn-sm"
            aria-label="Fechar"
          >
            <Icon name="x" size={18} />
          </button>
        </div>

        {!quiz ? (
          <span className="tag-mono muted">Carregando quiz…</span>
        ) : resultado ? (
          <div style={{ textAlign: "center", padding: "16px 4px" }}>
            <div
              style={{
                width: 76,
                height: 76,
                borderRadius: 18,
                margin: "0 auto 16px",
                display: "grid",
                placeItems: "center",
                background: resultado.aprovado
                  ? "rgba(34,197,94,0.12)"
                  : "rgba(229,55,43,0.12)",
                border: `1px solid ${resultado.aprovado ? "rgba(34,197,94,0.4)" : "rgba(229,55,43,0.4)"}`,
              }}
            >
              <Icon
                name={resultado.aprovado ? "checkCircle" : "x"}
                size={40}
                style={{
                  color: resultado.aprovado
                    ? "var(--success)"
                    : "var(--primary)",
                }}
              />
            </div>
            <h3 style={{ fontSize: "1.4rem", marginBottom: 6 }}>
              {resultado.aprovado ? "Aprovado! 🎉" : "Quase lá"}
            </h3>
            <p className="muted" style={{ marginBottom: 20 }}>
              Você acertou {resultado.corretas} de {resultado.total} (
              {resultado.nota.toFixed(0)}%). Nota de corte:{" "}
              {quiz.nota_corte.toFixed(0)}%.
            </p>
            <div
              className="flex center gap-2"
              style={{ justifyContent: "center" }}
            >
              {!resultado.aprovado && (
                <Button variant="primary" onClick={refazer}>
                  Tentar de novo
                </Button>
              )}
              <Button
                variant={resultado.aprovado ? "primary" : "ghost"}
                onClick={onClose}
              >
                Fechar
              </Button>
            </div>
          </div>
        ) : (
          <>
            <p
              className="muted"
              style={{ fontSize: "0.92rem", marginBottom: 18 }}
            >
              Responda todas as questões. Você precisa de{" "}
              <strong>{quiz.nota_corte.toFixed(0)}%</strong> para passar.
              {quiz.aprovado && " (Você já passou neste quiz.)"}
            </p>
            <div style={{ display: "grid", gap: 18 }}>
              {quiz.questoes.map((q, qi) => (
                <div key={q.id}>
                  <p style={{ fontWeight: 600, marginBottom: 10 }}>
                    {qi + 1}. {q.enunciado}
                  </p>
                  <div style={{ display: "grid", gap: 6 }}>
                    {q.alternativas.map((a) => (
                      <label
                        key={a.id}
                        className="flex center gap-2"
                        style={{
                          padding: "9px 12px",
                          borderRadius: 8,
                          cursor: "pointer",
                          background:
                            respostas[q.id] === a.id
                              ? "var(--primary-soft)"
                              : "var(--surface-2)",
                          border: `1px solid ${respostas[q.id] === a.id ? "var(--primary)" : "transparent"}`,
                        }}
                      >
                        <input
                          type="radio"
                          name={q.id}
                          checked={respostas[q.id] === a.id}
                          onChange={() =>
                            setRespostas((r) => ({ ...r, [q.id]: a.id }))
                          }
                        />
                        <span style={{ fontSize: "0.95rem" }}>{a.texto}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex center gap-2" style={{ marginTop: 22 }}>
              <Button
                variant="primary"
                disabled={!todas || enviar.isPending}
                onClick={() => enviar.mutate()}
              >
                {enviar.isPending ? "Enviando…" : "Enviar respostas"}
              </Button>
              <Button variant="ghost" onClick={onClose}>
                Cancelar
              </Button>
            </div>
            {enviar.isError && (
              <span
                className="tag-mono"
                style={{
                  color: "var(--danger)",
                  display: "block",
                  marginTop: 10,
                }}
              >
                Não foi possível enviar. Tente novamente.
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}
