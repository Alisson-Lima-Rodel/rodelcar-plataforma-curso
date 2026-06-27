"use client";

import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { BRAND } from "@/lib/portal-data";
import { usePortal } from "./portal-context";

interface FooterLink {
  t: string;
  href?: string;
  soon?: boolean;
}

const COLS: [string, FooterLink[]][] = [
  [
    "Portal",
    [
      { t: "Falar com a oficina" }, // ação: abre o dialog (WhatsApp)
      { t: "Câmbios automatizados", soon: true },
      { t: "Como funciona", soon: true },
      { t: "Garantia", soon: true },
    ],
  ],
  [
    "Cursos",
    [
      { t: "Formação Completa", href: "/#vitrine" },
      { t: "Cursos avulsos", href: "/cursos" },
      { t: "Certificados", soon: true },
      { t: "Comunidade", soon: true },
    ],
  ],
  [
    "Oficina",
    [
      { t: "Sobre a Rödelcar", soon: true },
      { t: "Localização", soon: true },
      { t: "Depoimentos", href: "/#prova" },
      { t: "Contato", href: `mailto:${BRAND.email}` },
    ],
  ],
];

const CHANNELS: [string, string, string][] = [
  ["youtube", "@rodelcar.cambio", BRAND.youtube],
  ["instagram", "@rodelcar.cambios", BRAND.instagram],
  ["threads", "@rodelcar.cambios", BRAND.threads],
  ["mail", BRAND.email, `mailto:${BRAND.email}`],
];

export function Footer() {
  const { openSchedule, showToast } = usePortal();

  const linkStyle = {
    color: "var(--text-subtle)",
    textDecoration: "none",
    fontSize: "0.9rem",
    transition: "color 150ms",
    cursor: "pointer",
  } as const;

  const onEnter = (e: React.MouseEvent<HTMLElement>) =>
    (e.currentTarget.style.color = "var(--text)");
  const onLeave = (e: React.MouseEvent<HTMLElement>) =>
    (e.currentTarget.style.color = "var(--text-subtle)");

  const renderLink = (it: FooterLink) => {
    if (it.t === "Falar com a oficina") {
      return (
        <button
          onClick={openSchedule}
          style={{
            ...linkStyle,
            background: "none",
            border: 0,
            padding: 0,
            textAlign: "left",
          }}
          onMouseEnter={onEnter}
          onMouseLeave={onLeave}
        >
          {it.t}
        </button>
      );
    }
    if (it.href) {
      if (it.href.startsWith("http")) {
        return (
          <a
            href={it.href}
            target="_blank"
            rel="noopener noreferrer"
            style={linkStyle}
            onMouseEnter={onEnter}
            onMouseLeave={onLeave}
          >
            {it.t}
          </a>
        );
      }
      if (it.href.startsWith("mailto:")) {
        return (
          <a
            href={it.href}
            style={linkStyle}
            onMouseEnter={onEnter}
            onMouseLeave={onLeave}
          >
            {it.t}
          </a>
        );
      }
      return (
        <Link
          href={it.href}
          style={linkStyle}
          onMouseEnter={onEnter}
          onMouseLeave={onLeave}
        >
          {it.t}
        </Link>
      );
    }
    // página ainda não publicada nesta fase
    return (
      <button
        onClick={() =>
          showToast({
            title: "Página em construção",
            msg: `"${it.t}" estará disponível em breve`,
          })
        }
        style={{
          ...linkStyle,
          background: "none",
          border: 0,
          padding: 0,
          textAlign: "left",
        }}
        onMouseEnter={onEnter}
        onMouseLeave={onLeave}
      >
        {it.t}
      </button>
    );
  };

  return (
    <footer
      style={{
        borderTop: "1px solid var(--border)",
        background: "var(--surface)",
        paddingTop: 56,
        paddingBottom: 32,
        marginTop: 24,
      }}
    >
      <div className="wrap">
        <div
          className="footer-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "1.4fr 1fr 1fr 1fr",
            gap: 32,
            marginBottom: 44,
          }}
        >
          <div>
            <div className="flex center gap-3" style={{ marginBottom: 16 }}>
              <Logo size="md" tagline={true} />
            </div>
            <p
              className="muted"
              style={{ fontSize: "0.9rem", maxWidth: 280, marginBottom: 18 }}
            >
              Especializada em câmbios automáticos e automatizados em Canoas-RS.
              Diagnóstico de bancada e formação técnica para mecânicos.
            </p>
            <div className="flex center gap-2" style={{ marginBottom: 18 }}>
              {CHANNELS.map(([ic, handle, url]) => (
                <a
                  key={ic}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={handle}
                  aria-label={handle}
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: 9,
                    border: "1px solid var(--border)",
                    background: "var(--surface-2)",
                    display: "grid",
                    placeItems: "center",
                    color: "var(--text-muted)",
                    transition: "all 150ms",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = "var(--primary)";
                    e.currentTarget.style.borderColor = "var(--primary)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = "var(--text-muted)";
                    e.currentTarget.style.borderColor = "var(--border)";
                  }}
                >
                  <Icon name={ic} size={18} />
                </a>
              ))}
            </div>
            <Button
              variant="secondary"
              size="sm"
              icon="whatsapp"
              onClick={openSchedule}
            >
              Falar com a oficina
            </Button>
          </div>
          {COLS.map(([h, items]) => (
            <div key={h}>
              <h4
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.72rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--text-muted)",
                  marginBottom: 16,
                  fontWeight: 500,
                }}
              >
                {h}
              </h4>
              <ul
                style={{
                  listStyle: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 11,
                }}
              >
                {items.map((it) => (
                  <li key={it.t}>{renderLink(it)}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="hr" style={{ marginBottom: 22 }} />
        <div
          className="flex center between"
          style={{ flexWrap: "wrap", gap: 12 }}
        >
          <span className="tag-mono">
            © 2026 RÖDELCAR · Especializada em Câmbios · Canoas-RS
          </span>
          <span className="tag-mono subtle">
            Automáticos · Automatizados · Dualogic · PowerShift · DSG
          </span>
        </div>
      </div>
    </footer>
  );
}
