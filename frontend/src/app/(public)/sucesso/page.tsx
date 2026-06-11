import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "@/components/ui/icon";

export const metadata: Metadata = {
  title: "Pagamento recebido",
  robots: { index: false, follow: false },
};

/** Destino da `success_url` do Stripe Checkout. Página é só UX: o acesso é
 * liberado pelo webhook (cartão = imediato; Pix confirma em alguns minutos). */
export default function SucessoPage() {
  return (
    <main>
      <section className="section blueprint" style={{ position: "relative" }}>
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
                background: "rgba(34,197,94,0.12)",
                border: "1px solid rgba(34,197,94,0.4)",
                display: "grid",
                placeItems: "center",
                margin: "0 auto 22px",
              }}
            >
              <Icon
                name="checkCircle"
                size={44}
                style={{ color: "var(--success)" }}
              />
            </div>
            <h1 style={{ fontSize: "2rem", marginBottom: 12 }}>
              Pagamento recebido!
            </h1>
            <p
              className="muted"
              style={{ fontSize: "1.05rem", lineHeight: 1.55, marginBottom: 8 }}
            >
              Seu acesso é liberado automaticamente assim que o pagamento é
              confirmado — no cartão isso é imediato.
            </p>
            <p
              className="muted"
              style={{
                fontSize: "0.92rem",
                lineHeight: 1.5,
                marginBottom: 28,
              }}
            >
              Pagou com Pix? A confirmação pode levar alguns minutos. Seus
              cursos aparecem no painel assim que ela chegar.
            </p>
            <div
              className="flex center gap-3"
              style={{ justifyContent: "center", flexWrap: "wrap" }}
            >
              <Link href="/painel" className="btn btn-primary btn-lg">
                <Icon name="bolt" size={18} />
                Ir para meus cursos
              </Link>
              <Link href="/" className="btn btn-secondary btn-lg">
                Voltar ao site
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
