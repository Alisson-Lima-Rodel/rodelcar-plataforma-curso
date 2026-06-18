"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { ApiError, confirmarResetSenha } from "@/lib/api";

export function ResetSenha() {
  const [token, setToken] = useState<string | null>(null);
  const [senha, setSenha] = useState("");
  const [confirma, setConfirma] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);

  // Lê o token da URL no cliente (evita o Suspense exigido por useSearchParams).
  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("token");
    setToken(t);
  }, []);

  const submit = async () => {
    if (busy) return;
    setError("");
    if (senha.length < 8) {
      setError("A senha deve ter ao menos 8 caracteres.");
      return;
    }
    if (senha !== confirma) {
      setError("As senhas não conferem.");
      return;
    }
    if (!token) {
      setError("Link inválido ou expirado. Peça um novo ao suporte.");
      return;
    }
    setBusy(true);
    try {
      await confirmarResetSenha(token, senha);
      setOk(true);
    } catch (e) {
      setError(
        e instanceof ApiError && e.code === "TOKEN_INVALIDO"
          ? "Link inválido ou expirado. Peça um novo ao suporte."
          : e instanceof ApiError && e.code === "RATE_LIMITED"
            ? "Muitas tentativas. Aguarde um instante e tente de novo."
            : "Não foi possível redefinir. Tente novamente.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
      }}
    >
      <form
        className="auth-card"
        style={{ maxWidth: 440, width: "100%" }}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <div style={{ marginBottom: 22 }}>
          <Logo size="sm" tagline={false} />
        </div>

        {ok ? (
          <div>
            <div
              className="flex center gap-3"
              style={{
                marginBottom: 16,
                padding: "12px 14px",
                borderRadius: 10,
                background: "rgba(34,197,94,0.1)",
                border: "1px solid rgba(34,197,94,0.35)",
              }}
            >
              <Icon
                name="checkCircle"
                size={18}
                style={{ color: "var(--success)", flexShrink: 0 }}
              />
              <span style={{ fontSize: "0.92rem" }}>
                Senha redefinida! Já pode entrar com a nova senha.
              </span>
            </div>
            <Link href="/login">
              <Button variant="primary" size="lg" block icon="arrow">
                Ir para o login
              </Button>
            </Link>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 22 }}>
              <h1 style={{ fontSize: "1.6rem", marginBottom: 6 }}>
                Redefinir senha
              </h1>
              <p className="muted" style={{ fontSize: "0.95rem" }}>
                Crie uma nova senha de acesso à plataforma.
              </p>
            </div>

            {error && (
              <div
                className="flex center gap-3"
                style={{
                  marginBottom: 16,
                  padding: "12px 14px",
                  borderRadius: 10,
                  background: "rgba(239,68,68,0.1)",
                  border: "1px solid rgba(239,68,68,0.35)",
                }}
              >
                <Icon
                  name="x"
                  size={18}
                  style={{ color: "var(--danger)", flexShrink: 0 }}
                />
                <span style={{ fontSize: "0.88rem" }}>{error}</span>
              </div>
            )}

            <div style={{ display: "grid", gap: 14, marginBottom: 18 }}>
              <div className="field">
                <label htmlFor="rs-senha">Nova senha</label>
                <div className="input-group">
                  <span className="ico">
                    <Icon name="lock" size={17} />
                  </span>
                  <input
                    id="rs-senha"
                    className="input"
                    type="password"
                    placeholder="••••••••"
                    value={senha}
                    onChange={(e) => setSenha(e.target.value)}
                  />
                </div>
                <span className="tag-mono subtle">Mín. 8 caracteres.</span>
              </div>
              <div className="field">
                <label htmlFor="rs-conf">Confirmar senha</label>
                <div className="input-group">
                  <span className="ico">
                    <Icon name="lock" size={17} />
                  </span>
                  <input
                    id="rs-conf"
                    className="input"
                    type="password"
                    placeholder="••••••••"
                    value={confirma}
                    onChange={(e) => setConfirma(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              block
              icon={busy ? undefined : "check"}
              disabled={busy}
            >
              {busy ? "Aguarde..." : "Redefinir senha"}
            </Button>
          </>
        )}
      </form>
    </div>
  );
}
