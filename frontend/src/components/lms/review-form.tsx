"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { enviarAvaliacao, getMinhaAvaliacao } from "@/lib/auth-api";

/** Formulário compacto de avaliação do curso (no card de "Meus cursos").
 *  Só aparece para quem tem o curso; o backend valida a matrícula. */
export function ReviewForm({ slug }: { slug: string }) {
  const qc = useQueryClient();
  const [aberto, setAberto] = useState(false);
  const [nota, setNota] = useState(0);
  const [hover, setHover] = useState(0);
  const [texto, setTexto] = useState("");

  const minhaQ = useQuery({
    queryKey: ["me", "avaliacao", slug],
    queryFn: () => getMinhaAvaliacao(slug),
    enabled: aberto,
  });

  useEffect(() => {
    if (minhaQ.data) {
      setNota(minhaQ.data.nota);
      setTexto(minhaQ.data.texto ?? "");
    }
  }, [minhaQ.data]);

  const salvar = useMutation({
    mutationFn: () => enviarAvaliacao(slug, nota, texto.trim() || null),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["me", "avaliacao", slug] }),
  });

  if (!aberto) {
    return (
      <Button
        variant="ghost"
        size="sm"
        icon="star"
        onClick={() => setAberto(true)}
      >
        Avaliar curso
      </Button>
    );
  }

  return (
    <div
      style={{
        width: "100%",
        marginTop: 12,
        paddingTop: 14,
        borderTop: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div className="flex center gap-1" aria-label="Sua nota">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onMouseEnter={() => setHover(n)}
            onMouseLeave={() => setHover(0)}
            onClick={() => setNota(n)}
            aria-label={`${n} estrela${n > 1 ? "s" : ""}`}
            style={{
              background: "none",
              border: 0,
              cursor: "pointer",
              padding: 2,
              lineHeight: 0,
            }}
          >
            <Icon
              name="star"
              size={24}
              style={{
                color:
                  (hover || nota) >= n
                    ? "var(--primary)"
                    : "var(--border-strong)",
              }}
            />
          </button>
        ))}
      </div>
      <textarea
        className="input"
        rows={3}
        maxLength={1000}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder="Conte como o curso te ajudou (opcional)"
        style={{ resize: "vertical" }}
      />
      <div className="flex center gap-2" style={{ flexWrap: "wrap" }}>
        <Button
          variant="primary"
          size="sm"
          disabled={nota === 0 || salvar.isPending}
          onClick={() => salvar.mutate()}
        >
          {salvar.isPending
            ? "Salvando…"
            : salvar.isSuccess
              ? "Avaliação salva ✓"
              : "Enviar avaliação"}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setAberto(false)}>
          Fechar
        </Button>
      </div>
    </div>
  );
}
