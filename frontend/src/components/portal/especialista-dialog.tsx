"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { telefoneValidoBR, useLeadWhatsapp } from "./whatsapp-lead";

export interface EspecialistaDialogProps {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
  cursoTitulo: string;
  cursoSlug: string;
}

const EMPTY = { nome: "", whatsapp: "", duvida: "" };

/** "Falar com especialista" na página do curso: nome, WhatsApp e a dúvida. Abre o
 *  WhatsApp da Rödelcar já com a dúvida + o curso que o aluno estava vendo, e
 *  registra o lead. Sem agendamento. */
export function EspecialistaDialog({
  open,
  onClose,
  onDone,
  cursoTitulo,
  cursoSlug,
}: EspecialistaDialogProps) {
  const [form, setForm] = useState(EMPTY);
  const [erros, setErros] = useState<{ nome?: string; whatsapp?: string; duvida?: string }>({});
  const { enviar, enviando } = useLeadWhatsapp(onDone);

  useEffect(() => {
    if (!open) {
      const t = setTimeout(() => {
        setForm(EMPTY);
        setErros({});
      }, 250);
      return () => clearTimeout(t);
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, onClose]);

  if (!open) return null;

  const set = (k: keyof typeof EMPTY, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = () => {
    if (enviando) return;
    const e: { nome?: string; whatsapp?: string; duvida?: string } = {};
    if (form.nome.trim().length < 2) e.nome = "Informe seu nome.";
    if (!telefoneValidoBR(form.whatsapp))
      e.whatsapp = "WhatsApp inválido — use DDD + número, ex.: (51) 99999-9999.";
    if (form.duvida.trim().length < 3) e.duvida = "Escreva sua dúvida.";
    setErros(e);
    if (Object.keys(e).length > 0) return;

    const nome = form.nome.trim();
    const whatsapp = form.whatsapp.trim();
    const duvida = form.duvida.trim();
    const texto =
      `Olá! Tenho uma dúvida sobre o curso *${cursoTitulo}*.\n` +
      `Nome: ${nome}\n` +
      `WhatsApp: ${whatsapp}\n` +
      `Dúvida: ${duvida}`;
    enviar(
      {
        nome,
        telefone: whatsapp,
        tipo_servico: "duvida_curso",
        mensagem: `Curso: ${cursoTitulo} · Dúvida: ${duvida}`,
        origem: `curso:${cursoSlug}`,
      },
      texto,
    );
  };

  return (
    <div className="overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label="Falar com especialista">
      <div className="dialog blueprint" onClick={(e) => e.stopPropagation()}>
        {/* header */}
        <div style={{ padding: "22px 26px", borderBottom: "1px solid var(--border)", position: "relative", zIndex: 1 }}>
          <div className="flex center between">
            <div className="flex center gap-3">
              <span
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: 10,
                  background: "var(--primary-soft)",
                  border: "1px solid rgba(229,55,43,0.4)",
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <Icon name="whatsapp" size={20} style={{ color: "var(--primary)" }} />
              </span>
              <div>
                <h3 style={{ fontSize: "1.18rem" }}>Falar com especialista</h3>
                <span className="tag-mono">Sobre: {cursoTitulo}</span>
              </div>
            </div>
            <button onClick={onClose} className="btn btn-ghost" style={{ width: 38, height: 38, padding: 0 }} aria-label="Fechar">
              <Icon name="x" size={18} />
            </button>
          </div>
        </div>

        {/* body */}
        <div style={{ padding: "24px 26px", position: "relative", zIndex: 1 }}>
          <div style={{ display: "grid", gap: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div className="field">
                <label htmlFor="esp-nome">Nome completo</label>
                <input
                  id="esp-nome"
                  className="input"
                  placeholder="Seu nome"
                  value={form.nome}
                  onChange={(e) => set("nome", e.target.value)}
                  aria-invalid={!!erros.nome}
                />
                {erros.nome && (
                  <span className="tag-mono" style={{ color: "var(--danger)", lineHeight: 1.4 }}>
                    {erros.nome}
                  </span>
                )}
              </div>
              <div className="field">
                <label htmlFor="esp-zap">WhatsApp</label>
                <input
                  id="esp-zap"
                  className="input"
                  type="tel"
                  inputMode="tel"
                  placeholder="(51) 99999-9999"
                  value={form.whatsapp}
                  onChange={(e) => set("whatsapp", e.target.value)}
                  aria-invalid={!!erros.whatsapp}
                />
                {erros.whatsapp && (
                  <span className="tag-mono" style={{ color: "var(--danger)", lineHeight: 1.4 }}>
                    {erros.whatsapp}
                  </span>
                )}
              </div>
            </div>
            <div className="field">
              <label htmlFor="esp-duvida">Sua dúvida</label>
              <textarea
                id="esp-duvida"
                className="textarea"
                placeholder="Sobre o que você quer saber antes de comprar?"
                value={form.duvida}
                onChange={(e) => set("duvida", e.target.value)}
                aria-invalid={!!erros.duvida}
              />
              {erros.duvida && (
                <span className="tag-mono" style={{ color: "var(--danger)", lineHeight: 1.4 }}>
                  {erros.duvida}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* footer */}
        <div
          style={{
            padding: "18px 26px",
            borderTop: "1px solid var(--border)",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            position: "relative",
            zIndex: 1,
          }}
        >
          <Button variant="primary" icon={enviando ? undefined : "whatsapp"} onClick={submit} disabled={enviando}>
            {enviando ? "Abrindo..." : "Enviar pelo WhatsApp"}
          </Button>
        </div>
      </div>
    </div>
  );
}
