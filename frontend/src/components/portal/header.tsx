"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Logo } from "@/components/ui/logo";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { usePortal } from "./portal-context";

const NAV: [string, string][] = [
  ["Portal", "/"],
  ["Cursos", "/#vitrine"],
  ["Depoimentos", "/#prova"],
];

export function Header() {
  const { openSchedule } = usePortal();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        borderBottom: "1px solid var(--border)",
        background: scrolled ? "rgba(19,22,28,0.92)" : "var(--surface)",
        backdropFilter: scrolled ? "blur(12px)" : "none",
        transition: "all 220ms ease-out",
      }}
    >
      <div className="wrap flex center between" style={{ height: 70 }}>
        <Link
          href="/"
          aria-label="RödelCar — início"
          style={{ display: "flex", alignItems: "center" }}
        >
          <Logo size="md" tagline={false} />
        </Link>
        <nav
          className="portal-nav flex center gap-6"
          style={{ fontSize: "0.92rem" }}
        >
          {NAV.map(([t, h]) => (
            <Link
              key={t}
              href={h}
              style={{
                color: "var(--text-muted)",
                textDecoration: "none",
                fontWeight: 500,
                transition: "color 150ms",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.color = "var(--text)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.color = "var(--text-muted)")
              }
            >
              {t}
            </Link>
          ))}
        </nav>
        <div className="flex center gap-3">
          <Link href="/login" className="btn btn-ghost btn-sm">
            <Icon name="lock" size={17} />
            Entrar
          </Link>
          <Button
            variant="primary"
            size="sm"
            icon="whatsapp"
            onClick={openSchedule}
          >
            Falar com a oficina
          </Button>
        </div>
      </div>
    </header>
  );
}
