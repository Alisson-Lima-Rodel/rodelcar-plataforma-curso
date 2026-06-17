"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { EntityManager } from "./entity-manager";
import type { AdminItem, EntitySchema } from "@/lib/admin-data";
import type { AdminCrud } from "@/lib/admin-api";

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
    <EntityManager
      ent={ent}
      items={items}
      onSave={onSave}
      onDelete={onDelete}
      onToast={onToast}
      autoNew={autoNew}
    />
  );
}
