"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { getIndicacoes } from "@/lib/auth-api";
import { SITE_URL } from "@/lib/seo";

/** Card "Indique e ganhe": link pessoal + status + cupons ganhos. */
export function ReferralCard() {
  const { data } = useQuery({
    queryKey: ["me", "indicacoes"],
    queryFn: getIndicacoes,
  });
  const [copied, setCopied] = useState(false);

  if (!data) return null;
  const link = `${SITE_URL}/login?ref=${encodeURIComponent(data.codigo)}`;
  const copiar = () => {
    if (navigator.clipboard)
      navigator.clipboard.writeText(link).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="card" style={{ padding: 22 }}>
      <div className="flex center gap-2" style={{ marginBottom: 8 }}>
        <Icon name="spark" size={18} style={{ color: "var(--primary)" }} />
        <h3 style={{ fontSize: "1.1rem" }}>Indique e ganhe</h3>
      </div>
      <p className="muted" style={{ fontSize: "0.92rem", marginBottom: 16 }}>
        Compartilhe seu link. Quando quem você indicou faz a 1ª compra,{" "}
        <strong style={{ color: "var(--text)" }}>
          vocês dois ganham 10% OFF
        </strong>{" "}
        na próxima.
      </p>

      <div
        className="flex center gap-2"
        style={{
          background: "var(--surface-2)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: "8px 8px 8px 14px",
          marginBottom: 16,
        }}
      >
        <span
          className="tag-mono"
          style={{
            flex: 1,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            fontSize: "0.82rem",
          }}
        >
          {link}
        </span>
        <Button
          variant="secondary"
          size="sm"
          icon={copied ? "check" : "file"}
          onClick={copiar}
        >
          {copied ? "Copiado" : "Copiar"}
        </Button>
      </div>

      <div
        className="flex center gap-6"
        style={{ flexWrap: "wrap", marginBottom: data.cupons.length ? 16 : 0 }}
      >
        <div>
          <div className="tag-mono subtle">Indicados</div>
          <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>
            {data.total_indicados}
          </div>
        </div>
        <div>
          <div className="tag-mono subtle">Recompensados</div>
          <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>
            {data.total_recompensados}
          </div>
        </div>
      </div>

      {data.cupons.length > 0 && (
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
          <div className="tag-mono subtle" style={{ marginBottom: 8 }}>
            SEUS CUPONS
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {data.cupons.map((c) => (
              <span
                key={c.codigo}
                className="badge"
                style={{
                  background: "var(--primary-soft)",
                  color: "var(--primary)",
                  borderColor: "var(--primary)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {c.codigo} ·{" "}
                {c.tipo === "percentual"
                  ? `${Math.round(c.valor)}% OFF`
                  : `R$ ${c.valor} OFF`}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
