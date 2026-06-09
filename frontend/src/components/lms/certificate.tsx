"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/components/providers/auth-provider";
import {
  emitirCertificado,
  getCursoPlayer,
  getMatriculas,
  type PlayerCurso,
} from "@/lib/auth-api";
import { lmsHref } from "@/lib/lms-nav";

function fmtDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function Certificate() {
  const router = useRouter();
  const qc = useQueryClient();
  const { aluno } = useAuth();
  const [querySlug, setQuerySlug] = useState<string | null | undefined>(
    undefined,
  );
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setQuerySlug(new URLSearchParams(window.location.search).get("slug"));
  }, []);

  const matQ = useQuery({
    queryKey: ["me", "matriculas"],
    queryFn: getMatriculas,
    enabled: querySlug === null,
  });
  const slug = querySlug || matQ.data?.items?.[0]?.curso.slug || null;

  const cursoQ = useQuery<PlayerCurso>({
    queryKey: ["me", "player", slug],
    queryFn: () => getCursoPlayer(slug as string),
    enabled: !!slug,
  });
  const data = cursoQ.data;

  const emitM = useMutation({
    mutationFn: (matriculaId: string) => emitirCertificado(matriculaId),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["me", "player", slug] }),
        qc.invalidateQueries({ queryKey: ["me", "dashboard"] }),
      ]);
    },
  });

  const cert = data?.certificado ?? null;
  const copy = () => {
    if (cert && navigator.clipboard)
      navigator.clipboard.writeText(cert.codigo).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const back = (
    <button
      className="btn btn-ghost btn-sm"
      style={{ paddingLeft: 0, marginBottom: 18 }}
      onClick={() => router.push(lmsHref("dashboard"))}
    >
      <Icon name="arrowLeft" size={16} /> Painel
    </button>
  );

  if ((querySlug === null && matQ.isLoading) || cursoQ.isLoading) {
    return (
      <div className="content">
        <span className="tag-mono muted">Carregando certificado…</span>
      </div>
    );
  }
  if (!slug || cursoQ.isError || !data) {
    return (
      <div className="content" style={{ maxWidth: 720 }}>
        {back}
        <div className="card" style={{ padding: 28, textAlign: "center" }}>
          <h3 style={{ fontSize: "1.15rem", marginBottom: 8 }}>
            Certificado indisponível
          </h3>
          <p className="muted" style={{ fontSize: "0.93rem" }}>
            Não foi possível carregar este curso.
          </p>
        </div>
      </div>
    );
  }

  // ── Curso ainda não concluído → não há certificado a emitir ────────────────
  if (!cert && !data.concluido) {
    return (
      <div className="content" style={{ maxWidth: 720 }}>
        {back}
        <div className="card" style={{ padding: 32, textAlign: "center" }}>
          <div className="cert-seal" style={{ opacity: 0.5 }}>
            <Icon name="award" size={40} stroke={2.2} />
          </div>
          <h3 style={{ fontSize: "1.3rem", margin: "16px 0 8px" }}>
            {data.curso.titulo}
          </h3>
          <p
            className="muted"
            style={{ fontSize: "0.95rem", marginBottom: 18 }}
          >
            Conclua todas as aulas para liberar seu certificado.
          </p>
          <div style={{ maxWidth: 360, margin: "0 auto 22px" }}>
            <div className="flex between" style={{ marginBottom: 7 }}>
              <span className="tag-mono">
                {Math.round(data.progresso_percentual)}% concluído
              </span>
            </div>
            <Progress value={data.progresso_percentual} />
          </div>
          <Button
            variant="primary"
            icon="play"
            onClick={() =>
              router.push(`${lmsHref("player")}?slug=${data.curso.slug}`)
            }
          >
            Retomar curso
          </Button>
        </div>
      </div>
    );
  }

  // ── Concluído, mas sem certificado emitido → emitir ────────────────────────
  if (!cert && data.concluido) {
    return (
      <div className="content" style={{ maxWidth: 720 }}>
        {back}
        <div
          className="card blueprint"
          style={{ padding: 36, textAlign: "center" }}
        >
          <div className="cert-seal">
            <Icon name="award" size={42} stroke={2.2} />
          </div>
          <Badge variant="success" icon="check">
            Curso concluído
          </Badge>
          <h3 style={{ fontSize: "1.5rem", margin: "16px 0 8px" }}>
            {data.curso.titulo}
          </h3>
          <p
            className="muted"
            style={{ fontSize: "0.95rem", marginBottom: 22 }}
          >
            Você concluiu todas as aulas. Emita seu certificado verificável.
          </p>
          {emitM.isError && (
            <p
              className="tag-mono"
              style={{ color: "var(--danger)", marginBottom: 14 }}
            >
              Não foi possível emitir agora. Tente novamente.
            </p>
          )}
          <Button
            variant="primary"
            size="lg"
            icon="award"
            onClick={() => emitM.mutate(data.matricula_id)}
            className={emitM.isPending ? "is-disabled" : ""}
          >
            {emitM.isPending ? "Emitindo…" : "Emitir certificado"}
          </Button>
        </div>
      </div>
    );
  }

  // ── Certificado emitido ─────────────────────────────────────────────────────
  const studentName = aluno?.nome ?? "Aluno(a)";
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
        <span className="tag-mono">Certificado · {cert!.codigo}</span>
      </div>

      <Reveal className="cert blueprint">
        <div style={{ position: "relative", zIndex: 1 }}>
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
            {data.curso.titulo}
          </h1>
          <p
            className="muted"
            style={{ fontSize: "1.02rem", marginBottom: 30 }}
          >
            concedido a{" "}
            <strong style={{ color: "var(--text)" }}>{studentName}</strong>
            {data.horas ? (
              <>
                {" "}
                por concluir a carga horária de{" "}
                <strong style={{ color: "var(--text)" }}>{data.horas}</strong>
              </>
            ) : null}
          </p>

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
                ["Emitido em", fmtDate(cert!.emitido_em)],
                ["Instrutor", "Equipe Rödelcar"],
                ["Carga horária", data.horas ?? "—"],
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
              {cert!.codigo}
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

      <div
        className="flex center"
        style={{
          justifyContent: "center",
          gap: 14,
          marginTop: 28,
          flexWrap: "wrap",
        }}
      >
        <Button
          variant="ghost"
          size="lg"
          onClick={() => router.push(lmsHref("dashboard"))}
        >
          Voltar ao painel
        </Button>
      </div>
    </div>
  );
}
