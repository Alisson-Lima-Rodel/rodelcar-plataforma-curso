"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { consultarStatusCompra } from "@/lib/auth-api";

/** A página é destino da `success_url` do Stripe. Como o acesso é concedido SÓ
 *  pelo webhook (que pode atrasar ou, mal configurado, nem chegar), NÃO afirmamos
 *  "pago" de cara: consultamos o status real (`?session_id=...`) e fazemos um
 *  polling curto, mostrando "confirmando…", "liberado" ou "ainda processando". */

type Fase =
  | "carregando" // 1ª consulta em andamento
  | "liberado" // matrícula ativa já existe → pode entrar
  | "processando" // pago no Stripe, webhook ainda não liberou
  | "pendente" // pagamento não confirmado (ex.: Pix)
  | "demorando" // estourou o tempo sem liberar
  | "indefinido"; // sem session_id / não autenticado → mensagem neutra

const INTERVALO_MS = 2500;
const MAX_TENTATIVAS = 16; // ~40s

function Spinner() {
  return (
    <div
      aria-hidden
      style={{
        width: 40,
        height: 40,
        borderRadius: "50%",
        border: "3px solid var(--border)",
        borderTopColor: "var(--primary)",
        animation: "rc-spin 0.8s linear infinite",
      }}
    />
  );
}

export default function SucessoCliente() {
  const [fase, setFase] = useState<Fase>("carregando");

  useEffect(() => {
    const sessionId = new URLSearchParams(window.location.search).get(
      "session_id",
    );
    if (!sessionId) {
      setFase("indefinido");
      return;
    }

    let vivo = true;
    let timer: ReturnType<typeof setTimeout>;
    let tentativas = 0;

    const tick = async () => {
      tentativas += 1;
      try {
        const s = await consultarStatusCompra(sessionId);
        if (!vivo) return;
        if (s.estado === "liberado") {
          setFase("liberado");
          return; // para o polling
        }
        setFase(s.estado === "pendente" ? "pendente" : "processando");
      } catch {
        // 401 (não logado) / 404 (sessão não é desta conta) → não dá pra
        // confirmar: cai na mensagem neutra em vez de afirmar "pago".
        if (!vivo) return;
        setFase("indefinido");
        return;
      }
      if (tentativas >= MAX_TENTATIVAS) {
        setFase("demorando");
        return;
      }
      timer = setTimeout(tick, INTERVALO_MS);
    };

    tick();
    return () => {
      vivo = false;
      clearTimeout(timer);
    };
  }, []);

  const liberado = fase === "liberado";
  const aguardando =
    fase === "carregando" || fase === "processando" || fase === "pendente";

  return (
    <section className="section blueprint" style={{ position: "relative" }}>
      <style>{`@keyframes rc-spin{to{transform:rotate(360deg)}}`}</style>
      <div className="wrap" style={{ maxWidth: 640 }}>
        <div
          className="card"
          style={{ padding: "48px 44px", textAlign: "center" }}
        >
          <div
            style={{
              width: 84,
              height: 84,
              borderRadius: 20,
              background: liberado
                ? "rgba(34,197,94,0.12)"
                : fase === "demorando"
                  ? "rgba(245,158,11,0.12)"
                  : "var(--surface-2)",
              border: liberado
                ? "1px solid rgba(34,197,94,0.4)"
                : fase === "demorando"
                  ? "1px solid rgba(245,158,11,0.4)"
                  : "1px solid var(--border)",
              display: "grid",
              placeItems: "center",
              margin: "0 auto 22px",
            }}
          >
            {liberado ? (
              <Icon
                name="checkCircle"
                size={44}
                style={{ color: "var(--success)" }}
              />
            ) : aguardando ? (
              <Spinner />
            ) : (
              <Icon
                name="clock"
                size={40}
                style={{ color: "var(--text-muted)" }}
              />
            )}
          </div>

          <h1 style={{ fontSize: "2rem", marginBottom: 12 }}>
            {liberado
              ? "Pagamento confirmado!"
              : fase === "demorando"
                ? "Estamos processando"
                : fase === "indefinido"
                  ? "Recebemos sua solicitação"
                  : "Confirmando seu pagamento…"}
          </h1>

          <p
            className="muted"
            style={{ fontSize: "1.05rem", lineHeight: 1.55, marginBottom: 8 }}
          >
            {liberado
              ? "Tudo certo — seu acesso já está liberado. Bons estudos!"
              : fase === "demorando"
                ? "A confirmação está demorando mais que o normal. Seu acesso é liberado automaticamente assim que o pagamento confirmar."
                : fase === "indefinido"
                  ? "Se você concluiu uma compra, o acesso é liberado automaticamente assim que o pagamento é confirmado."
                  : "Estamos confirmando seu pagamento com o provedor. Isso costuma levar só alguns segundos."}
          </p>

          {!liberado && (
            <p
              className="muted"
              style={{ fontSize: "0.92rem", lineHeight: 1.5, marginBottom: 28 }}
            >
              {fase === "pendente"
                ? "Pagou com Pix? A confirmação pode levar alguns minutos — você não precisa ficar nesta tela."
                : fase === "demorando"
                  ? "Se em alguns minutos os cursos não aparecerem no painel, fale com o suporte."
                  : "Você não precisa atualizar a página — ela confirma sozinha."}
            </p>
          )}
          {liberado && <div style={{ marginBottom: 28 }} />}

          <div
            className="flex center gap-3"
            style={{ justifyContent: "center", flexWrap: "wrap" }}
          >
            {liberado ? (
              <Link href="/painel" className="btn btn-primary btn-lg">
                <Icon name="bolt" size={18} />
                Ir para meus cursos
              </Link>
            ) : (
              <Link href="/painel" className="btn btn-secondary btn-lg">
                Ver meu painel
              </Link>
            )}
            <Link href="/" className="btn btn-secondary btn-lg">
              Voltar ao site
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
