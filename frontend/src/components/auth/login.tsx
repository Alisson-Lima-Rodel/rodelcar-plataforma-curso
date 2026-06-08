"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { useAuth } from "@/components/providers/auth-provider";
import { ApiError } from "@/lib/api";

type Mode = "login" | "signup" | "recover";

const TITLES: Record<Mode, { h: string; s: string }> = {
  login: { h: "Entrar na plataforma", s: "Acesse seus cursos e certificados." },
  signup: { h: "Criar sua conta", s: "Comece sua formação em câmbios hoje." },
  recover: { h: "Recuperar acesso", s: "Enviaremos um link de redefinição." },
};

function mensagemErro(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === "CREDENCIAIS_INVALIDAS")
      return "E-mail ou senha incorretos.";
    if (e.code === "EMAIL_JA_CADASTRADO")
      return "Já existe uma conta com esse e-mail.";
    if (e.code === "RATE_LIMITED")
      return "Muitas tentativas. Aguarde um instante e tente de novo.";
    if (e.code === "VALIDATION_ERROR") return "Confira os dados informados.";
    return e.message;
  }
  return "Não foi possível concluir. Tente novamente.";
}

export function Login() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const submit = async () => {
    if (busy) return;
    setError("");
    if (mode === "recover") {
      setNotice(
        "Se houver uma conta com esse e-mail, enviamos um link de redefinição.",
      );
      setMode("login");
      return;
    }
    setBusy(true);
    try {
      if (mode === "login") await login(email.trim(), senha);
      else await register(nome.trim(), email.trim(), senha);
      router.push("/painel");
    } catch (e) {
      setError(mensagemErro(e));
    } finally {
      setBusy(false);
    }
  };

  const cta =
    mode === "login"
      ? "Entrar"
      : mode === "signup"
        ? "Criar conta"
        : "Enviar link de redefinição";
  const icon =
    mode === "login" ? "lock" : mode === "signup" ? "spark" : "arrow";

  return (
    <div className="auth">
      {/* aside */}
      <div className="auth-aside blueprint">
        <div
          className="glow-amber"
          style={{ width: 520, height: 420, top: -160, left: -80 }}
        />
        <button
          onClick={() => router.push("/")}
          className="btn btn-ghost btn-sm"
          style={{
            paddingLeft: 0,
            position: "relative",
            zIndex: 1,
            alignSelf: "flex-start",
          }}
        >
          <Icon name="arrowLeft" size={16} /> Voltar ao site
        </button>
        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ marginBottom: 28 }}>
            <Logo size="lg" tagline={true} />
          </div>
          <h2
            style={{
              fontSize: "2.1rem",
              lineHeight: 1.1,
              marginBottom: 16,
              maxWidth: 380,
            }}
          >
            A bancada de elite em câmbio, agora no seu computador.
          </h2>
          <ul
            style={{
              listStyle: "none",
              display: "grid",
              gap: 13,
              maxWidth: 360,
            }}
          >
            {[
              "Cursos de Dualogic, PowerShift, iMotion, DSG e mais",
              "1 ano de acesso e certificado verificável",
              "Comunidade fechada com a equipe Rödelcar",
            ].map((t, i) => (
              <li
                key={i}
                className="flex gap-3"
                style={{ alignItems: "flex-start" }}
              >
                <Icon
                  name="checkCircle"
                  size={19}
                  style={{
                    color: "var(--primary)",
                    flexShrink: 0,
                    marginTop: 1,
                  }}
                />
                <span
                  style={{ color: "var(--text-muted)", fontSize: "0.96rem" }}
                >
                  {t}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <span
          className="tag-mono subtle"
          style={{ position: "relative", zIndex: 1 }}
        >
          Canoas-RS · @rodelcar.cambio
        </span>
      </div>

      {/* form */}
      <div className="auth-main">
        <form
          className="auth-card"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <div style={{ marginBottom: 24 }}>
            <h1 style={{ fontSize: "1.7rem", marginBottom: 6 }}>
              {TITLES[mode].h}
            </h1>
            <p className="muted" style={{ fontSize: "0.96rem" }}>
              {TITLES[mode].s}
            </p>
          </div>

          {notice && (
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
              <span style={{ fontSize: "0.88rem", color: "var(--text)" }}>
                {notice}
              </span>
            </div>
          )}
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
              <span style={{ fontSize: "0.88rem", color: "var(--text)" }}>
                {error}
              </span>
            </div>
          )}

          <div style={{ display: "grid", gap: 14, marginBottom: 18 }}>
            {mode === "signup" && (
              <div className="field">
                <label htmlFor="au-nome">Nome completo</label>
                <div className="input-group">
                  <span className="ico">
                    <Icon name="users" size={17} />
                  </span>
                  <input
                    id="au-nome"
                    className="input"
                    placeholder="Seu nome"
                    value={nome}
                    onChange={(e) => setNome(e.target.value)}
                  />
                </div>
              </div>
            )}
            <div className="field">
              <label htmlFor="au-email">E-mail</label>
              <div className="input-group">
                <span className="ico">
                  <Icon name="message" size={17} />
                </span>
                <input
                  id="au-email"
                  className="input"
                  type="email"
                  placeholder="voce@oficina.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              {mode === "login" && (
                <span className="tag-mono subtle" style={{ lineHeight: 1.4 }}>
                  Seu nível de acesso (aluno ou administrador) é identificado
                  automaticamente.
                </span>
              )}
            </div>
            {mode !== "recover" && (
              <div className="field">
                <div className="flex between center">
                  <label htmlFor="au-senha">Senha</label>
                  {mode === "login" && (
                    <button
                      type="button"
                      onClick={() => {
                        setMode("recover");
                        setError("");
                      }}
                      style={{
                        background: "none",
                        border: 0,
                        cursor: "pointer",
                        fontSize: "0.82rem",
                        color: "var(--accent)",
                        padding: 0,
                      }}
                    >
                      Esqueci minha senha
                    </button>
                  )}
                </div>
                <div className="input-group">
                  <span className="ico">
                    <Icon name="lock" size={17} />
                  </span>
                  <input
                    id="au-senha"
                    className="input"
                    type="password"
                    placeholder="••••••••"
                    value={senha}
                    onChange={(e) => setSenha(e.target.value)}
                  />
                </div>
              </div>
            )}
          </div>

          {/* ação dominante */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            block
            icon={busy ? undefined : icon}
            disabled={busy}
          >
            {busy ? "Aguarde..." : cta}
          </Button>

          <div className="hr" style={{ margin: "22px 0" }} />
          <div style={{ textAlign: "center" }}>
            {mode === "login" ? (
              <span className="muted" style={{ fontSize: "0.9rem" }}>
                Ainda não tem conta?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("signup");
                    setError("");
                    setNotice("");
                  }}
                  style={{
                    background: "none",
                    border: 0,
                    color: "var(--primary)",
                    cursor: "pointer",
                    fontWeight: 600,
                    fontSize: "0.9rem",
                  }}
                >
                  Criar conta
                </button>
              </span>
            ) : (
              <span className="muted" style={{ fontSize: "0.9rem" }}>
                Já tem conta?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("login");
                    setError("");
                  }}
                  style={{
                    background: "none",
                    border: 0,
                    color: "var(--primary)",
                    cursor: "pointer",
                    fontWeight: 600,
                    fontSize: "0.9rem",
                  }}
                >
                  Entrar
                </button>
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
