"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { EntityManager, type RowAction } from "./entity-manager";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import type { AdminItem, EntitySchema } from "@/lib/admin-data";
import {
  bloquearAluno,
  recuperarSenhaAluno,
  type AdminCrud,
} from "@/lib/admin-api";

/** Link de redefinição gerado pelo admin, com atalhos p/ WhatsApp e e-mail. */
function ResetLinkModal({
  aluno,
  link,
  onClose,
}: {
  aluno: AdminItem;
  link: string;
  onClose: () => void;
}) {
  const [copiado, setCopiado] = useState(false);
  const nome = String(aluno.nome ?? "aluno");
  const tel = String(aluno.telefone ?? "").replace(/\D/g, "");
  const email = String(aluno.email ?? "");
  const msg = `Olá, ${nome}! Para redefinir a sua senha na RödelCar, acesse: ${link} (válido por 24h).`;
  const whatsapp = tel
    ? `https://wa.me/55${tel}?text=${encodeURIComponent(msg)}`
    : null;
  const mailto = email
    ? `mailto:${email}?subject=${encodeURIComponent(
        "Redefinição de senha — RödelCar",
      )}&body=${encodeURIComponent(msg)}`
    : null;

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1800);
    } catch {
      /* clipboard pode falhar sem https — o link fica visível p/ copiar à mão */
    }
  };

  return (
    <>
      <div className="sheet-overlay" onClick={onClose} />
      <div className="sheet" role="dialog" aria-modal="true">
        <div className="sheet-head">
          <div>
            <h3 style={{ fontSize: "1.1rem" }}>Recuperar senha</h3>
            <span className="tag-mono">{nome}</span>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Fechar">
            <Icon name="x" size={17} />
          </button>
        </div>
        <div className="sheet-body">
          <p className="muted" style={{ fontSize: "0.9rem", marginBottom: 14 }}>
            Link de redefinição (válido por 24h, uso único). Envie ao aluno por
            WhatsApp ou e-mail.
          </p>
          <div
            className="input-group"
            style={{ marginBottom: 14, alignItems: "stretch" }}
          >
            <input className="input" readOnly value={link} />
            <button
              className="icon-btn"
              onClick={copiar}
              aria-label="Copiar link"
              title="Copiar"
            >
              <Icon name={copiado ? "check" : "file"} size={16} />
            </button>
          </div>
          <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
            <a
              href={whatsapp ?? undefined}
              target="_blank"
              rel="noreferrer"
              style={{
                flex: 1,
                pointerEvents: whatsapp ? "auto" : "none",
                opacity: whatsapp ? 1 : 0.4,
              }}
            >
              <Button variant="primary" block icon="whatsapp">
                WhatsApp
              </Button>
            </a>
            <a
              href={mailto ?? undefined}
              style={{
                flex: 1,
                pointerEvents: mailto ? "auto" : "none",
                opacity: mailto ? 1 : 0.4,
              }}
            >
              <Button variant="secondary" block icon="mail">
                E-mail
              </Button>
            </a>
          </div>
          {!whatsapp && (
            <p className="tag-mono muted" style={{ marginTop: 10 }}>
              Sem telefone cadastrado — use o e-mail ou copie o link.
            </p>
          )}
        </div>
      </div>
    </>
  );
}

/** Igual ao EntityManager, mas os itens vêm da API e as mutações vão pro backend. */
export function RemoteEntityManager({
  ent,
  entityKey,
  crud,
  autoNew,
  onToast,
}: {
  ent: EntitySchema;
  entityKey: string;
  crud: AdminCrud;
  autoNew?: boolean;
  onToast: (msg: string) => void;
}) {
  const qc = useQueryClient();
  const queryKey = ["admin", entityKey];
  const [resetFor, setResetFor] = useState<{ aluno: AdminItem; link: string } | null>(
    null,
  );
  const { data, isLoading, isError } = useQuery({
    queryKey,
    queryFn: crud.list,
  });
  // O form genérico é escalar; campos de lista (ex.: idiomas_legenda do curso)
  // chegam como array da API → viram texto "PT, EN" no form e voltam a array no
  // save. Localizado aqui para não vazar arrays pelo AdminItem.
  const items = ((data ?? []) as Record<string, unknown>[]).map((it) =>
    Array.isArray(it.idiomas_legenda)
      ? { ...it, idiomas_legenda: (it.idiomas_legenda as string[]).join(", ") }
      : it,
  ) as AdminItem[];

  const onSave = async (item: AdminItem) => {
    const exists = items.some((x) => x.id === item.id);
    const { id, ...rest } = item; // id do backend não vai no corpo
    const payload: Record<string, unknown> = { ...rest };
    if (typeof payload.idiomas_legenda === "string") {
      payload.idiomas_legenda = payload.idiomas_legenda
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }
    try {
      if (exists) await crud.update(String(id), payload);
      else await crud.create(payload);
      await qc.invalidateQueries({ queryKey });
    } catch {
      onToast("Não foi possível salvar — confira os campos.");
    }
  };

  const onDelete = async (id: string) => {
    try {
      await crud.remove(id);
      await qc.invalidateQueries({ queryKey });
    } catch {
      onToast("Não foi possível excluir.");
    }
  };

  // Ativar/inativar curso direto na linha (à esquerda do editar).
  const courseActions: RowAction[] = [
    {
      label: (it) => (it.ativo ? "Inativar curso" : "Ativar curso"),
      icon: () => "power",
      tone: (it) => (it.ativo ? "success" : "default"),
      onClick: async (it) => {
        try {
          await crud.update(String(it.id), { ativo: !it.ativo });
          await qc.invalidateQueries({ queryKey });
          onToast(it.ativo ? "Curso inativado" : "Curso ativado");
        } catch {
          onToast("Não foi possível alterar o curso.");
        }
      },
    },
  ];

  // Bloquear/desbloquear + recuperar senha do aluno.
  const studentActions: RowAction[] = [
    {
      label: (it) => (it.bloqueado ? "Desbloquear acesso" : "Bloquear acesso"),
      icon: () => "lock",
      tone: (it) => (it.bloqueado ? "danger" : "default"),
      onClick: async (it) => {
        try {
          await bloquearAluno(String(it.id), !it.bloqueado);
          await qc.invalidateQueries({ queryKey });
          onToast(it.bloqueado ? "Acesso liberado" : "Acesso bloqueado");
        } catch {
          onToast("Não foi possível alterar o acesso.");
        }
      },
    },
    {
      label: () => "Recuperar senha",
      icon: () => "key",
      onClick: async (it) => {
        try {
          const r = await recuperarSenhaAluno(String(it.id));
          const link = `${window.location.origin}/recuperar-senha?token=${r.token}`;
          setResetFor({ aluno: it, link });
        } catch {
          onToast("Não foi possível gerar o link.");
        }
      },
    },
  ];

  const extraActions =
    entityKey === "courses"
      ? courseActions
      : entityKey === "students"
        ? studentActions
        : undefined;

  if (isLoading) {
    return (
      <div className="content">
        <span className="tag-mono muted">
          Carregando {ent.label.toLowerCase()}…
        </span>
      </div>
    );
  }
  if (isError) {
    return (
      <div className="content">
        <span className="tag-mono" style={{ color: "var(--danger)" }}>
          Falha ao carregar. Sua sessão pode ter expirado — saia e entre de
          novo.
        </span>
      </div>
    );
  }
  return (
    <>
      <EntityManager
        ent={ent}
        items={items}
        onSave={onSave}
        onDelete={onDelete}
        onToast={onToast}
        autoNew={autoNew}
        extraActions={extraActions}
      />
      {resetFor && (
        <ResetLinkModal
          aluno={resetFor.aluno}
          link={resetFor.link}
          onClose={() => setResetFor(null)}
        />
      )}
    </>
  );
}
