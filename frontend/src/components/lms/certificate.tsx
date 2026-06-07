"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { CERT } from "@/lib/student-data";
import { lmsHref } from "@/lib/lms-nav";

export function Certificate() {
  const router = useRouter();
  const [copied, setCopied] = useState(false);
  const copy = () => {
    if (navigator.clipboard)
      navigator.clipboard.writeText(CERT.code).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="content" style={{ maxWidth: 880 }}>
      <div
        className="flex center between"
        style={{ marginBottom: 22, gap: 12, flexWrap: "wrap" }}
      >
        <button
          className="btn btn-ghost btn-sm"
          style={{ paddingLeft: 0 }}
          onClick={() => router.push(lmsHref("dashboard"))}
        >
          <Icon name="arrowLeft" size={16} /> Painel
        </button>
        <span className="tag-mono">Certificado · {CERT.code}</span>
      </div>

      <Reveal className="cert blueprint">
        <div style={{ position: "relative", zIndex: 1 }}>
          {/* seal */}
          <div className="cert-seal">
            <Icon name="award" size={46} stroke={2.2} />
          </div>
          <Badge variant="success" icon="check">
            Conclusão verificada
          </Badge>

          <div
            className="tag-mono"
            style={{ margin: "26px 0 10px", letterSpacing: "0.12em" }}
          >
            CERTIFICADO DE CONCLUSÃO
          </div>
          <h1
            style={{
              fontSize: "2.3rem",
              marginBottom: 8,
              maxWidth: 560,
              marginInline: "auto",
              lineHeight: 1.1,
            }}
          >
            {CERT.course}
          </h1>
          <p
            className="muted"
            style={{ fontSize: "1.02rem", marginBottom: 30 }}
          >
            concedido a{" "}
            <strong style={{ color: "var(--text)" }}>{CERT.student}</strong> por
            concluir a carga horária de{" "}
            <strong style={{ color: "var(--text)" }}>{CERT.hours}</strong>
          </p>

          {/* meta row */}
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 40,
              marginBottom: 32,
              flexWrap: "wrap",
            }}
          >
            {(
              [
                ["Emitido em", CERT.date],
                ["Instrutor", CERT.instructor],
                ["Carga horária", CERT.hours],
              ] as [string, string][]
            ).map(([l, v], i) => (
              <div key={i} style={{ textAlign: "center" }}>
                <div className="tag-mono subtle" style={{ marginBottom: 4 }}>
                  {l}
                </div>
                <div style={{ fontWeight: 600, fontSize: "0.98rem" }}>{v}</div>
              </div>
            ))}
          </div>

          {/* código de verificação em mono */}
          <div style={{ marginBottom: 8 }}>
            <div className="tag-mono subtle" style={{ marginBottom: 10 }}>
              CÓDIGO DE VERIFICAÇÃO
            </div>
            <button
              className="cert-code"
              onClick={copy}
              style={{ cursor: "pointer" }}
              title="Copiar código"
            >
              {CERT.code}
              <Icon
                name={copied ? "check" : "file"}
                size={16}
                style={{ color: copied ? "var(--success)" : "var(--primary)" }}
              />
            </button>
            <div className="tag-mono subtle" style={{ marginTop: 12 }}>
              verifique em rodelcar.com/verificar{" "}
              {copied && <span className="amber"> · código copiado</span>}
            </div>
          </div>
        </div>
      </Reveal>

      {/* ações — uma única dominante */}
      <div
        className="flex center"
        style={{
          justifyContent: "center",
          gap: 14,
          marginTop: 28,
          flexWrap: "wrap",
        }}
      >
        <Button variant="primary" size="lg" icon="download">
          Baixar certificado (PDF)
        </Button>
        <Button variant="secondary" size="lg" icon="users">
          Compartilhar no LinkedIn
        </Button>
        <Button
          variant="ghost"
          size="lg"
          onClick={() => router.push(lmsHref("dashboard"))}
        >
          Voltar ao painel
        </Button>
      </div>

      {/* próximo passo */}
      <Reveal
        className="card blueprint"
        style={{
          marginTop: 36,
          padding: "28px 32px",
          position: "relative",
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 24,
          flexWrap: "wrap",
        }}
      >
        <div
          className="glow-amber"
          style={{ width: 300, height: 200, top: -80, right: -40 }}
        />
        <div style={{ position: "relative", zIndex: 1 }}>
          <Badge variant="cyan" icon="bolt">
            Próximo passo
          </Badge>
          <h3 style={{ fontSize: "1.3rem", margin: "12px 0 6px" }}>
            Continue para o Câmbio Automático Convencional
          </h3>
          <p className="muted" style={{ fontSize: "0.94rem" }}>
            Você está a 4 aulas de mais um certificado.
          </p>
        </div>
        <Button
          variant="secondary"
          size="lg"
          iconRight="arrow"
          onClick={() => router.push(lmsHref("player"))}
          style={{ position: "relative", zIndex: 1, flexShrink: 0 }}
        >
          Retomar curso
        </Button>
      </Reveal>
    </div>
  );
}
