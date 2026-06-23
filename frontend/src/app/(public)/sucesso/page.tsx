import type { Metadata } from "next";
import SucessoCliente from "./sucesso-cliente";

export const metadata: Metadata = {
  title: "Pagamento recebido",
  robots: { index: false, follow: false },
};

/** Destino da `success_url` do Stripe Checkout. O acesso é concedido SÓ pelo
 * webhook — então a UI (cliente) consulta o status real da sessão e só afirma
 * "pago" quando a matrícula existe, em vez de assumir sucesso pelo redirect. */
export default function SucessoPage() {
  return (
    <main>
      <SucessoCliente />
    </main>
  );
}
