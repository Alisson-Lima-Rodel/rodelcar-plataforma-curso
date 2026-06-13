import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { verificarCertificado } from "@/lib/api";

interface Params {
  params: { codigo: string };
}

// Páginas de certificado individual não vão para o índice dos buscadores.
export const metadata: Metadata = {
  title: "Verificação de certificado",
  robots: { index: false, follow: false },
};

function fmtData(iso: string): string {
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

export default async function VerificarPage({ params }: Params) {
  const codigo = decodeURIComponent(params.codigo);
  const cert = await verificarCertificado(codigo);

  return (
    <main>
      <section className="section blueprint" style={{ position: "relative" }}>
        <div className="wrap" style={{ maxWidth: 640 }}>
          <div className="card" style={{ padding: "44px 40px" }}>
            {cert ? (
              <>
                <div
                  style={{
                    width: 76,
                    height: 76,
                    borderRadius: 18,
                    background: "rgba(34,197,94,0.12)",
                    border: "1px solid rgba(34,197,94,0.4)",
                    display: "grid",
                    placeItems: "center",
                    margin: "0 auto 20px",
                  }}
                >
                  <Icon
                    name="checkCircle"
                    size={40}
                    style={{ color: "var(--success)" }}
                  />
                </div>
                <h1
                  style={{
                    fontSize: "1.5rem",
                    textAlign: "center",
                    marginBottom: 6,
                  }}
                >
                  Certificado válido
                </h1>
                <p
                  className="muted"
                  style={{ textAlign: "center", marginBottom: 28 }}
                >
                  Emitido pela RödelCar e autenticado pelo código abaixo.
                </p>
                <dl style={{ display: "grid", gap: 16 }}>
                  {(
                    [
                      ["Titular", cert.aluno_nome],
                      ["Curso", cert.curso],
                      ["Emitido em", fmtData(cert.emitido_em)],
                      ["Código", codigo],
                    ] as [string, string][]
                  ).map(([rotulo, valor]) => (
                    <div
                      key={rotulo}
                      className="flex between"
                      style={{
                        gap: 16,
                        paddingBottom: 12,
                        borderBottom: "1px solid var(--border)",
                      }}
                    >
                      <dt className="tag-mono subtle">{rotulo}</dt>
                      <dd
                        style={{
                          fontWeight: 600,
                          textAlign: "right",
                          margin: 0,
                        }}
                      >
                        {valor}
                      </dd>
                    </div>
                  ))}
                </dl>
              </>
            ) : (
              <>
                <div
                  style={{
                    width: 76,
                    height: 76,
                    borderRadius: 18,
                    background: "rgba(229,55,43,0.12)",
                    border: "1px solid rgba(229,55,43,0.4)",
                    display: "grid",
                    placeItems: "center",
                    margin: "0 auto 20px",
                  }}
                >
                  <Icon
                    name="x"
                    size={40}
                    style={{ color: "var(--primary)" }}
                  />
                </div>
                <h1
                  style={{
                    fontSize: "1.5rem",
                    textAlign: "center",
                    marginBottom: 6,
                  }}
                >
                  Certificado não encontrado
                </h1>
                <p
                  className="muted"
                  style={{ textAlign: "center", marginBottom: 8 }}
                >
                  Não há certificado com o código{" "}
                  <strong style={{ color: "var(--text)" }}>{codigo}</strong>.
                  Confira se digitou corretamente.
                </p>
              </>
            )}
            <div style={{ textAlign: "center", marginTop: 30 }}>
              <Link href="/" className="btn btn-secondary">
                Ir para o site da RödelCar
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
