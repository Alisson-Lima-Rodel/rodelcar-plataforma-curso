"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Stars } from "@/components/ui/stars";
import { ApiError } from "@/lib/api";
import { uploadImagem } from "@/lib/admin-api";
import {
  uid,
  type AdminItem,
  type BadgeVariant,
  type Column,
  type EntitySchema,
  type FieldDef,
} from "@/lib/admin-data";

function initialsOf(name: string) {
  return (name || "?")
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}
function fmtDate(d: string) {
  if (!d) return "—";
  const [y, m, dd] = d.split("-");
  return `${dd}/${m}/${y}`;
}

const STATUS_MAP: Record<string, BadgeVariant> = {
  Ativo: "success",
  Publicado: "success",
  Aprovado: "success",
  Inativo: "",
  "Em desenvolvimento": "warning",
  Bloqueado: "warning",
  Rascunho: "warning",
  Pendente: "warning",
};
const ROLE_MAP: Record<string, BadgeVariant> = {
  Administrador: "amber",
  Editor: "cyan",
  Suporte: "",
};
const SYSTEM_MAP: Record<string, BadgeVariant> = {
  Automatizado: "amber",
  Automático: "cyan",
  "Dupla embreagem": "premium",
};

function Cell({ col, item }: { col: Column; item: AdminItem }) {
  const v = item[col.key];
  const s = String(v ?? "");
  switch (col.kind) {
    case "user":
      return (
        <div className="cell-user">
          <span className="cell-avatar">{initialsOf(s)}</span>
          <div>
            <div className="cell-strong">{s}</div>
            {item.email && <div className="tag-mono">{item.email}</div>}
          </div>
        </div>
      );
    case "strong":
      return <span className="cell-strong">{s}</span>;
    case "center":
      return (
        <span
          style={{
            display: "block",
            textAlign: "center",
            fontFamily: "var(--font-mono)",
          }}
        >
          {s}
        </span>
      );
    case "price":
      return (
        <span className="mono" style={{ fontWeight: 600 }}>
          R$ {s}
        </span>
      );
    case "date":
      return <span className="tag-mono">{fmtDate(s)}</span>;
    case "stars":
      return <Stars value={Number(v)} size={14} />;
    case "truncate":
      return (
        <span
          className="muted"
          style={{
            display: "block",
            maxWidth: 260,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {s}
        </span>
      );
    case "badgeStatus":
      return <Badge variant={STATUS_MAP[s] ?? ""}>{s}</Badge>;
    case "badgePlan":
      return (
        <Badge variant={v === "Premium Anual" ? "premium" : ""}>{s}</Badge>
      );
    case "badgeRole":
      return (
        <Badge
          variant={ROLE_MAP[s] ?? ""}
          icon={v === "Administrador" ? "shield" : undefined}
        >
          {s}
        </Badge>
      );
    case "muted":
      return <span className="tag-mono">{s || "—"}</span>;
    case "badgeAtivo":
      return (
        <Badge variant={v ? "success" : ""}>{v ? "Ativo" : "Inativo"}</Badge>
      );
    case "badgeSystem":
      return <Badge variant={SYSTEM_MAP[s] ?? ""}>{s}</Badge>;
    default:
      return <span>{s}</span>;
  }
}

const IMG_FORMATOS = ["image/png", "image/jpeg", "image/webp"];
const IMG_MAX_MB = 5;
const IMG_REGRAS = `PNG, JPG ou WebP · até ${IMG_MAX_MB} MB`;

function ImageField({
  f,
  value,
  onChange,
}: {
  f: FieldDef;
  value: string | number | boolean | null | undefined;
  onChange: (v: string) => void;
}) {
  const wrap = f.col === "full" ? "full" : "";
  const url = typeof value === "string" ? value : "";
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState("");

  const escolher = async (file: File | undefined) => {
    if (!file) return;
    setErro("");
    // Valida no cliente ANTES de enviar (feedback imediato); o backend revalida.
    if (!IMG_FORMATOS.includes(file.type)) {
      setErro(`Formato não aceito. Use ${IMG_REGRAS}.`);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (file.size > IMG_MAX_MB * 1024 * 1024) {
      const mb = (file.size / 1024 / 1024).toFixed(1).replace(".", ",");
      setErro(`Imagem de ${mb} MB excede o limite de ${IMG_MAX_MB} MB.`);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setBusy(true);
    try {
      onChange(await uploadImagem(file));
    } catch (e) {
      setErro(
        e instanceof ApiError && e.code === "STORAGE_NAO_CONFIGURADO"
          ? "Upload indisponível — storage de imagens não configurado."
          : e instanceof ApiError
            ? e.message
            : "Falha ao enviar a imagem.",
      );
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className={`field ${wrap}`.trim()}>
      <label>{f.label}</label>
      <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
        <div
          style={{
            width: 132,
            height: 74,
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: url
              ? `center/cover no-repeat url(${url})`
              : "var(--surface-2)",
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
          }}
        >
          {!url && (
            <Icon
              name="book"
              size={22}
              style={{ color: "var(--text-subtle)" }}
            />
          )}
        </div>
        <div className="flex col gap-2">
          <input
            ref={inputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            style={{ display: "none" }}
            onChange={(e) => escolher(e.target.files?.[0])}
          />
          <div className="flex center gap-2" style={{ flexWrap: "wrap" }}>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              icon="download"
              onClick={() => inputRef.current?.click()}
              disabled={busy}
            >
              {busy ? "Enviando..." : url ? "Trocar imagem" : "Enviar imagem"}
            </Button>
            {url && (
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost btn-sm"
              >
                Ver / baixar
              </a>
            )}
            {url && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => onChange("")}
                disabled={busy}
              >
                Remover
              </button>
            )}
          </div>
          <span
            className="tag-mono subtle"
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <Icon name="shield" size={13} />
            {IMG_REGRAS}
          </span>
          {erro && (
            <span
              className="tag-mono flex center gap-1"
              style={{ color: "var(--danger)" }}
            >
              <Icon name="x" size={13} />
              {erro}
            </span>
          )}
        </div>
      </div>
      {f.hint && (
        <span className="tag-mono subtle" style={{ lineHeight: 1.4 }}>
          {f.hint}
        </span>
      )}
    </div>
  );
}

function Field({
  f,
  value,
  onChange,
}: {
  f: FieldDef;
  value: string | number | boolean | null | undefined;
  onChange: (v: string | number | boolean) => void;
}) {
  const wrap = f.col === "full" ? "full" : "";
  if (f.type === "image") {
    return <ImageField f={f} value={value} onChange={onChange} />;
  }
  if (f.type === "toggle") {
    const on = value === f.on;
    return (
      <div
        className={`field ${wrap}`.trim()}
        style={{
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "4px 0",
        }}
      >
        <label style={{ margin: 0 }}>{f.label}</label>
        <label className="switch">
          <input
            type="checkbox"
            checked={on}
            onChange={(e) =>
              onChange(e.target.checked ? (f.on ?? "") : (f.off ?? ""))
            }
          />
          <span className="track" />
          <span className="knob" />
        </label>
      </div>
    );
  }
  if (f.type === "stars") {
    return (
      <div className={`field ${wrap}`.trim()}>
        <label>{f.label}</label>
        <div className="star-input">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              className={n <= Number(value) ? "on" : ""}
              onClick={() => onChange(n)}
              aria-label={`${n} estrelas`}
            >
              <Icon name="star" size={24} />
            </button>
          ))}
        </div>
      </div>
    );
  }
  return (
    <div className={`field ${wrap}`.trim()}>
      <label>{f.label}</label>
      {f.type === "select" ? (
        <select
          className="select"
          value={value as string | undefined}
          onChange={(e) => onChange(e.target.value)}
        >
          {f.options?.map((o) => (
            <option key={o}>{o}</option>
          ))}
        </select>
      ) : f.type === "textarea" ? (
        <textarea
          className="textarea"
          value={value as string | undefined}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          className="input"
          type={
            f.type === "number"
              ? "number"
              : f.type === "date"
                ? "date"
                : f.type === "password"
                  ? "password"
                  : "text"
          }
          placeholder={f.type === "password" ? "••••••••" : undefined}
          value={(value ?? "") as string | number}
          onChange={(e) =>
            onChange(
              f.type === "number" ? Number(e.target.value) : e.target.value,
            )
          }
        />
      )}
      {f.hint && (
        <span className="tag-mono subtle" style={{ lineHeight: 1.4 }}>
          {f.hint}
        </span>
      )}
    </div>
  );
}

function FormSheet({
  ent,
  item,
  onClose,
  onSave,
}: {
  ent: EntitySchema;
  item: AdminItem | null;
  onClose: () => void;
  onSave: (it: AdminItem) => void;
}) {
  const [draft, setDraft] = useState<AdminItem>(item || { ...ent.defaults });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);
  const set = (k: string, v: string | number | boolean) =>
    setDraft((d) => ({ ...d, [k]: v }));
  const isEdit = !!item;
  const valid = ent.fields
    .filter(
      (f) => f.type === "text" && (f.key === "nome" || f.key === "titulo"),
    )
    .every((f) => String(draft[f.key] || "").trim());

  return (
    <>
      <div className="sheet-overlay" onClick={onClose} />
      <div className="sheet" role="dialog" aria-modal="true">
        <div className="sheet-head">
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
              <Icon
                name={ent.icon}
                size={19}
                style={{ color: "var(--primary)" }}
              />
            </span>
            <div>
              <h3 style={{ fontSize: "1.1rem" }}>
                {isEdit ? "Editar" : "Novo"} {ent.singular}
              </h3>
              <span className="tag-mono">
                {isEdit ? "Atualizar cadastro" : "Preencha os dados"}
              </span>
            </div>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Fechar">
            <Icon name="x" size={17} />
          </button>
        </div>
        <div className="sheet-body">
          <div className="form-grid">
            {ent.fields.map((f) => (
              <Field
                key={f.key}
                f={f}
                value={draft[f.key]}
                onChange={(v) => set(f.key, v)}
              />
            ))}
          </div>
        </div>
        <div className="sheet-foot">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            icon="check"
            onClick={() => valid && onSave({ ...draft, id: draft.id || uid() })}
            className={valid ? "" : "is-disabled"}
          >
            {isEdit ? "Salvar alterações" : "Cadastrar"}
          </Button>
        </div>
      </div>
    </>
  );
}

function Confirm({
  label,
  onCancel,
  onConfirm,
}: {
  label: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="overlay" onClick={onCancel}>
      <div className="dialog confirm" onClick={(e) => e.stopPropagation()}>
        <div className="flex center gap-3" style={{ marginBottom: 14 }}>
          <span
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)",
              display: "grid",
              placeItems: "center",
            }}
          >
            <Icon name="x" size={20} style={{ color: "var(--danger)" }} />
          </span>
          <h3 style={{ fontSize: "1.1rem" }}>Excluir registro</h3>
        </div>
        <p className="muted" style={{ fontSize: "0.94rem", marginBottom: 22 }}>
          Tem certeza que deseja excluir{" "}
          <strong style={{ color: "var(--text)" }}>{label}</strong>? Esta ação
          não pode ser desfeita.
        </p>
        <div className="flex" style={{ justifyContent: "flex-end", gap: 12 }}>
          <Button variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
          <button
            className="btn"
            style={{ background: "var(--danger)", color: "#fff" }}
            onClick={onConfirm}
          >
            <Icon name="x" size={16} /> Excluir
          </button>
        </div>
      </div>
    </div>
  );
}

/** Ação extra por linha (ex.: ativar/inativar curso, bloquear/recuperar aluno).
 * Renderizada à esquerda do botão de editar. `active` (opcional) escolhe o ícone/
 * cor conforme um estado do item (toggle). */
export interface RowAction {
  label: (it: AdminItem) => string;
  icon: (it: AdminItem) => string;
  tone?: (it: AdminItem) => "success" | "danger" | "default";
  onClick: (it: AdminItem) => void;
}

export interface EntityManagerProps {
  ent: EntitySchema;
  items: AdminItem[];
  onSave: (item: AdminItem) => void;
  onDelete: (id: string) => void;
  onToast: (msg: string) => void;
  autoNew?: boolean;
  extraActions?: RowAction[];
}

export function EntityManager({
  ent,
  items,
  onSave,
  onDelete,
  onToast,
  autoNew,
  extraActions,
}: EntityManagerProps) {
  const [q, setQ] = useState("");
  // Filtro pode ter um padrão próprio (ex.: cursos abrem em "Ativo + Em
  // desenvolvimento", escondendo os inativos) e um matcher custom.
  const [filter, setFilter] = useState(ent.filter.initial ?? "Todos");
  const [editing, setEditing] = useState<AdminItem | null>(autoNew ? {} : null);
  const [confirm, setConfirm] = useState<AdminItem | null>(null);

  const cap = (s: string) => s[0].toUpperCase() + s.slice(1);

  const filtered = items.filter((it) => {
    const okQ = !q || ent.search(it).toLowerCase().includes(q.toLowerCase());
    const okF = ent.filter.match
      ? ent.filter.match(it, filter)
      : filter === "Todos" || it[ent.filter.key] === filter;
    return okQ && okF;
  });

  const save = (item: AdminItem) => {
    const existed = items.some((x) => x.id === item.id);
    onSave(item);
    setEditing(null);
    onToast(`${cap(ent.singular)} ${existed ? "atualizado" : "cadastrado"}`);
  };
  const del = () => {
    if (!confirm) return;
    onDelete(String(confirm.id));
    onToast(`${cap(ent.singular)} excluído`);
    setConfirm(null);
  };

  return (
    <div className="content" style={{ maxWidth: 1180 }}>
      {/* toolbar — ação âmbar única */}
      <div className="toolbar">
        <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
          <div className="search">
            <Icon name="gauge" size={16} />
            <input
              placeholder={`Buscar ${ent.label.toLowerCase()}...`}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div className="seg">
            {ent.filter.options.map((o) => (
              <button
                key={o}
                className={filter === o ? "active" : ""}
                onClick={() => setFilter(o)}
              >
                {o}
              </button>
            ))}
          </div>
        </div>
        <Button variant="primary" icon="spark" onClick={() => setEditing({})}>
          Novo {ent.singular}
        </Button>
      </div>

      {/* table */}
      {filtered.length ? (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                {ent.columns.map((c) => (
                  <th
                    key={c.key}
                    style={
                      c.kind === "center" ? { textAlign: "center" } : undefined
                    }
                  >
                    {c.label}
                  </th>
                ))}
                <th style={{ textAlign: "right" }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((it) => (
                <tr key={String(it.id)}>
                  {ent.columns.map((c) => (
                    <td key={c.key}>
                      <Cell col={c} item={it} />
                    </td>
                  ))}
                  <td>
                    <div className="row-actions">
                      {extraActions?.map((a, ai) => {
                        const tone = a.tone?.(it) ?? "default";
                        return (
                          <button
                            key={ai}
                            className={`icon-btn${tone === "danger" ? " danger" : ""}`}
                            onClick={() => a.onClick(it)}
                            aria-label={a.label(it)}
                            title={a.label(it)}
                            style={
                              tone === "success"
                                ? { color: "var(--success)" }
                                : undefined
                            }
                          >
                            <Icon name={a.icon(it)} size={15} />
                          </button>
                        );
                      })}
                      <button
                        className="icon-btn"
                        onClick={() => setEditing(it)}
                        aria-label="Editar"
                      >
                        <Icon name="wrench" size={15} />
                      </button>
                      <button
                        className="icon-btn danger"
                        onClick={() => setConfirm(it)}
                        aria-label="Excluir"
                      >
                        <Icon name="x" size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="tbl-wrap">
          <div className="empty">
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                display: "grid",
                placeItems: "center",
                margin: "0 auto 16px",
              }}
            >
              <Icon
                name={ent.icon}
                size={26}
                style={{ color: "var(--text-muted)" }}
              />
            </div>
            <h3 style={{ fontSize: "1.1rem", marginBottom: 6 }}>
              Nenhum {ent.singular} encontrado
            </h3>
            <p className="muted" style={{ marginBottom: 18 }}>
              Ajuste a busca/filtro ou cadastre um novo.
            </p>
            <Button
              variant="secondary"
              icon="spark"
              onClick={() => setEditing({})}
            >
              Novo {ent.singular}
            </Button>
          </div>
        </div>
      )}

      <div className="flex center between" style={{ marginTop: 16 }}>
        <span className="tag-mono">
          {filtered.length} de {items.length} {ent.label.toLowerCase()}
        </span>
      </div>

      {editing !== null && (
        <FormSheet
          ent={ent}
          item={editing.id ? editing : null}
          onClose={() => setEditing(null)}
          onSave={save}
        />
      )}
      {confirm && (
        <Confirm
          label={ent.title(confirm)}
          onCancel={() => setConfirm(null)}
          onConfirm={del}
        />
      )}
    </div>
  );
}
