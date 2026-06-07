"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { Badge } from "@/components/ui/badge";
import { Stars } from "@/components/ui/stars";
import type { Course } from "@/lib/portal-data";

export function CourseCard({ c }: { c: Course }) {
  return (
    <Link
      href={`/cursos/${c.id}`}
      className="card card-hover"
      style={{
        padding: 14,
        display: "flex",
        flexDirection: "column",
        cursor: "pointer",
        height: "100%",
        textDecoration: "none",
        color: "inherit",
      }}
    >
      <div className="thumb" style={{ marginBottom: 14 }}>
        <Icon
          name={c.icon}
          size={34}
          style={{ color: "var(--border-strong)" }}
        />
        <span
          className="badge"
          style={{
            position: "absolute",
            top: 9,
            left: 9,
            padding: "4px 9px",
            background: "rgba(10,12,16,0.8)",
          }}
        >
          {c.badge.label}
        </span>
        <span className="thumb-label">[ capa · {c.id} ]</span>
      </div>
      <div
        style={{
          padding: "0 4px",
          display: "flex",
          flexDirection: "column",
          flex: 1,
        }}
      >
        <div className="flex center gap-2" style={{ marginBottom: 9 }}>
          <span className="tag-mono">
            <Stars value={c.rating} size={12} />
          </span>
          <span className="tag-mono">
            {c.rating} · {c.students.toLocaleString("pt-BR")} alunos
          </span>
        </div>
        <h3
          style={{
            fontSize: "1.18rem",
            marginBottom: 8,
            lineHeight: 1.18,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            minHeight: "2.36em",
          }}
        >
          {c.title}
        </h3>
        <p
          className="muted"
          style={{
            fontSize: "0.9rem",
            marginBottom: 14,
            flex: 1,
            lineHeight: 1.45,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            minHeight: "2.6em",
          }}
        >
          {c.tagline}
        </p>
        <div className="flex center gap-3" style={{ marginBottom: 14 }}>
          <Badge icon="clock">{c.hours}</Badge>
          <Badge icon="book">{c.lessons} aulas</Badge>
          <Badge variant="cyan" icon="infinity">
            1 ano
          </Badge>
        </div>
        <div className="hr" style={{ marginBottom: 14 }} />
        <div className="flex center between">
          <div className="flex center gap-2">
            <span className="price" style={{ fontSize: "1.5rem" }}>
              R$ {c.price}
            </span>
            {c.old && (
              <span className="strike tag-mono" style={{ fontSize: "0.82rem" }}>
                R$ {c.old}
              </span>
            )}
          </div>
          <span className="btn btn-secondary btn-sm">
            Ver curso
            <Icon name="chevronRight" size={17} />
          </span>
        </div>
      </div>
    </Link>
  );
}
