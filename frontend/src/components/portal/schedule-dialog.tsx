"use client";

import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { createLead, ApiError } from "@/lib/api";

export interface ScheduleDialogProps {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
}

const SLOTS = ["Seg 09:00", "Seg 14:00", "Ter 10:30", "Qua 08:00", "Qua 16:00", "Qui 11:00"];
const EMPTY = { nome: "", whatsapp: "", veiculo: "", cambio: "Automático convencional", sintoma: "" };

export function ScheduleDialog({ open, onClose, onDone }: ScheduleDialogProps) {
  const [step, setStep] = useState(1);
  const [slot, setSlot] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY);

  const mutation = useMutation({
    mutationFn: createLead,
    onSuccess: () => onDone(),
  });

  useEffect(() => {
    if (!open) {
      const t = setTimeout(() => {
        setStep(1);
        setSlot(null);
        setForm(EMPTY);
        mutation.reset();
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
  const canContinue = form.nome.trim().length >= 2 && form.whatsapp.trim().length >= 8;

  const submit = () => {
    if (mutation.isPending) return;
    mutation.mutate({
      nome: form.nome.trim(),
      telefone: form.whatsapp.trim(),
      tipo_servico: "avaliacao_cambio",
      mensagem: `Veículo: ${form.veiculo || "—"} · Câmbio: ${form.cambio} · Sintoma: ${form.sintoma || "—"} · Horário: ${slot ?? "a combinar"}`,
      origem: "agendamento_portal",
    });
  };

  const errMsg =
    mutation.error instanceof ApiError
      ? mutation.error.code === "RATE_LIMITED"
        ? "Muitas tentativas. Aguarde um instante e tente de novo."
        : mutation.error.message
      : mutation.isError
        ? "Não foi possível enviar. Tente novamente."
        : null;

  return (
    <div className="overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label="Agendar avaliação">
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
                <Icon name="calendar" size={20} style={{ color: "var(--primary)" }} />
              </span>
              <div>
                <h3 style={{ fontSize: "1.18rem" }}>Agendar avaliação</h3>
                <span className="tag-mono">Diagnóstico técnico · 45 min</span>
              </div>
            </div>
            <button onClick={onClose} className="btn btn-ghost" style={{ width: 38, height: 38, padding: 0 }} aria-label="Fechar">
              <Icon name="x" size={18} />
            </button>
          </div>
          {/* steps indicator */}
          <div className="flex center gap-2" style={{ marginTop: 18 }}>
            {[1, 2].map((s) => (
              <div
                key={s}
                style={{
                  flex: 1,
                  height: 4,
                  borderRadius: 9999,
                  background: s <= step ? "var(--primary)" : "var(--border-strong)",
                  transition: "background 250ms",
                }}
              />
            ))}
          </div>
        </div>

        {/* body */}
        <div style={{ padding: "24px 26px", position: "relative", zIndex: 1 }}>
          {step === 1 && (
            <div style={{ display: "grid", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div className="field">
                  <label htmlFor="sd-nome">Nome completo</label>
                  <input id="sd-nome" className="input" placeholder="Seu nome" value={form.nome} onChange={(e) => set("nome", e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="sd-zap">WhatsApp</label>
                  <input id="sd-zap" className="input" placeholder="(00) 00000-0000" value={form.whatsapp} onChange={(e) => set("whatsapp", e.target.value)} />
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div className="field">
                  <label htmlFor="sd-veiculo">Veículo</label>
                  <input id="sd-veiculo" className="input" placeholder="Ex.: Corolla 2018" value={form.veiculo} onChange={(e) => set("veiculo", e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="sd-cambio">Câmbio</label>
                  <select id="sd-cambio" className="select" value={form.cambio} onChange={(e) => set("cambio", e.target.value)}>
                    <option>Automático convencional</option>
                    <option>CVT</option>
                    <option>Dupla embreagem (DCT)</option>
                    <option>Não sei</option>
                  </select>
                </div>
              </div>
              <div className="field">
                <label htmlFor="sd-sintoma">Sintoma principal</label>
                <textarea
                  id="sd-sintoma"
                  className="textarea"
                  placeholder="Descreva o que está acontecendo: trancos, patinação, luz no painel..."
                  value={form.sintoma}
                  onChange={(e) => set("sintoma", e.target.value)}
                />
              </div>
            </div>
          )}
          {step === 2 && (
            <div>
              <label style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--text-muted)", display: "block", marginBottom: 12 }}>
                Escolha um horário disponível
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 8 }}>
                {SLOTS.map((s) => (
                  <button
                    key={s}
                    onClick={() => setSlot(s)}
                    className="btn"
                    style={{
                      background: slot === s ? "var(--primary-soft)" : "var(--surface-2)",
                      borderColor: slot === s ? "var(--primary)" : "var(--border)",
                      color: slot === s ? "var(--primary)" : "var(--text)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.84rem",
                      padding: "12px 8px",
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
              <div
                className="flex center gap-3"
                style={{ marginTop: 18, padding: "14px 16px", background: "var(--surface-2)", borderRadius: 10, border: "1px solid var(--border)" }}
              >
                <Icon name="shield" size={20} style={{ color: "var(--success)", flexShrink: 0 }} />
                <span className="muted" style={{ fontSize: "0.86rem" }}>
                  Avaliação sem compromisso. Você recebe o laudo técnico mesmo que decida não fechar o serviço.
                </span>
              </div>
              {errMsg && (
                <div className="flex center gap-2" style={{ marginTop: 12, color: "var(--danger)", fontSize: "0.85rem" }}>
                  <Icon name="x" size={15} /> {errMsg}
                </div>
              )}
            </div>
          )}
        </div>

        {/* footer */}
        <div
          style={{
            padding: "18px 26px",
            borderTop: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            position: "relative",
            zIndex: 1,
          }}
        >
          {step === 1 ? (
            <span className="tag-mono">Passo 1 de 2 · Seus dados</span>
          ) : (
            <button onClick={() => setStep(1)} className="btn btn-ghost btn-sm" disabled={mutation.isPending}>
              <Icon name="arrowLeft" size={16} /> Voltar
            </button>
          )}
          {step === 1 ? (
            <Button variant="primary" iconRight="arrow" onClick={() => setStep(2)} disabled={!canContinue}>
              Continuar
            </Button>
          ) : (
            <Button variant="primary" icon={mutation.isPending ? undefined : "check"} onClick={submit} disabled={mutation.isPending}>
              {mutation.isPending ? "Enviando..." : "Confirmar agendamento"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
