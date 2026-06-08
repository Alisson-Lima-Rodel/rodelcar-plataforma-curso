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
  const items = (data ?? []) as AdminItem[];

  const onSave = async (item: AdminItem) => {
    const exists = items.some((x) => x.id === item.id);
    const { id, ...rest } = item; // id do backend não vai no corpo
    try {
      if (exists) await crud.update(String(id), rest);
      else await crud.create(rest);
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
