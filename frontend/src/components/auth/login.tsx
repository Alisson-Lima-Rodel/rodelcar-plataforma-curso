"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { useAuth } from "@/components/providers/auth-provider";
import { ApiError } from "@/lib/api";
import { adminLogin } from "@/lib/admin-api";
import {
  executarCompra,
  lerCompraPendente,
  limparCompraPendente,
} from "@/lib/checkout-api";

type Mode = "login" | "signup" | "recover";

const TITLES: Record<Mode, { h: string; s: string }> = {
  login: { h: "Entrar na plataforma", s: "Acesse seus cursos e certificados." },
  signup: { h: "Criar sua conta", s: "Comece sua formação em câmbios hoje." },
  recover: { h: "Recuperar acesso", s: "Enviaremos um link de redefinição." },
};

const SENHA_MIN = 8;

/** Extrai do envelope 422 (`details`) uma mensagem amigável por campo. Não ecoa
 * o valor digitado — o backend já remove `input` dos detalhes (LGPD). */
function mensagemValidacao(details: unknown): string | null {
  if (!Array.isArray(details)) return null;
  for (const d of details) {
    const loc = (d?.loc ?? []) as unknown[];
    const campo = String(loc[loc.length - 1] ?? "");
    const tipo = String(d?.type ?? "");
    if (campo === "senha")
      return tipo.includes("too_long")
        ? "A senha pode ter no máximo 72 caracteres."
        : `A senha precisa ter pelo menos ${SENHA_MIN} caracteres.`;
    if (campo === "email") return "Informe um e-mail válido.";
    if (campo === "nome") return "Informe seu nome completo.";
  }
  return null;
}

function mensagemErro(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === "CREDENCIAIS_INVALIDAS")
      return "E-mail ou senha incorretos.";
    if (e.code === "EMAIL_JA_CADASTRADO")
      return "Já existe uma conta com esse e-mail.";
    if (e.code === "RATE_LIMITED")
      return "Muitas tentativas. Aguarde um instante e tente de novo.";
    if (e.code === "VALIDATION_ERROR")
      return mensagemValidacao(e.details) ?? "Confira os dados informados.";
    return e.message;
  }
  return "Não foi possível concluir. Tente novamente.";
}

export function Login() {
  const router = useRouter();
  const { login, register, aluno, logout } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [telefone, setTelefone] = useState("");
  const [senha, setSenha] = useState("");
  const [showSenha, setShowSenha] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [ref, setRef] = useState<string | null>(null);
  // Compra pendente vinda do site público: se já houver sessão salva, em vez de
  // comprar com ela direto, confirmamos quem é o usuário (item 4.1).
  const [temCompra, setTemCompra] = useState(false);
  const [trocarConta, setTrocarConta] = useState(false);

  // Compra iniciada no portal sem login: avisa e retoma após entrar/cadastrar.
  // Link de indicação (?ref=): já abre no cadastro e guarda o código.
  useEffect(() => {
    if (lerCompraPendente()) {
      setTemCompra(true);
      setNotice("Entre ou crie sua conta para concluir a compra.");
    }
    const params = new URLSearchParams(window.location.search);
    if (params.get("sessao") === "expirada") {
      setNotice("Sua sessão expirou. Entre novamente para continuar.");
    }
    const r = new URLSearchParams(window.location.search).get("ref");
    if (r) {
      setRef(r);
      setMode("signup");
      setNotice(
        "Você foi indicado! Crie sua conta e ganhe um cupom na 1ª compra.",
      );
    }
  }, []);

  /** Pós-login do aluno: retoma a compra pendente (redireciona p/ a Stripe) ou
   * segue para o painel. */
  const concluirEntrada = async () => {
    const intent = lerCompraPendente();
    if (intent) {
      try {
        await executarCompra(intent); // window.location → Stripe
        return;
      } catch {
        limparCompraPendente(); // compra falhou; segue p/ o painel (pode tentar de novo)
      }
    }
    router.push("/painel");
  };

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
    if (mode === "signup") {
      if (nome.trim().length < 2) {
        setError("Informe seu nome completo (mínimo 2 caracteres).");
        return;
      }
      // WhatsApp obrigatório: DDD + número (10 ou 11 dígitos; aceita máscara/+55).
      const digitos = telefone
        .replace(/\D/g, "")
        .replace(/^55(?=\d{10,11}$)/, "");
      if (digitos.length < 10 || digitos.length > 11) {
        setError("Informe um WhatsApp válido com DDD (ex.: (51) 99999-9999).");
        return;
      }
      if (senha.length < SENHA_MIN) {
        setError(`A senha precisa ter pelo menos ${SENHA_MIN} caracteres.`);
        return;
      }
    }
    setBusy(true);
    try {
      if (mode === "signup") {
        await register(nome.trim(), email.trim(), senha, telefone.trim(), ref);
        await concluirEntrada();
      } else {
        // Uma única tela de login: tenta admin primeiro; se a conta não for
        // admin (401), entra como aluno. O nível de acesso é o da conta.
        try {
          await adminLogin(email.trim(), senha);
          router.push("/admin");
          return;
        } catch (e) {
          if (!(e instanceof ApiError) || e.status !== 401) throw e;
        }
        await login(email.trim(), senha);
        await concluirEntrada();
      }
    } catch (e) {
      setError(mensagemErro(e));
    } finally {
      setBusy(false);
    }
  };

  // Confirmação de compra: há compra pendente E já existe um aluno logado, e o
  // usuário ainda não pediu para trocar de conta.
  const confirmando = temCompra && !!aluno && !trocarConta;

  const continuarComoLogado = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await concluirEntrada();
    } finally {
      setBusy(false);
    }
  };

  const entrarOutraConta = async () => {
    await logout(); // limpa a sessão salva (como abrir em janela anônima)
    setTrocarConta(true);
    setMode("login");
    setNotice("Entre ou crie sua conta para concluir a compra.");
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
          {/* Topo só no mobile: o aside (com marca + "voltar") fica oculto,
              então repõe aqui a logo e a saída para o site. */}
          <div className="auth-mobile-top">
            <button
              type="button"
              onClick={() => router.push("/")}
              className="btn btn-ghost btn-sm"
              style={{ paddingLeft: 0 }}
            >
              <Icon name="arrowLeft" size={16} /> Voltar ao site
            </button>
            <Logo size="sm" tagline={false} />
          </div>

          <div style={{ marginBottom: 24 }}>
            <h1 style={{ fontSize: "1.7rem", marginBottom: 6 }}>
              {confirmando ? "Confirmar conta" : TITLES[mode].h}
            </h1>
            <p className="muted" style={{ fontSize: "0.96rem" }}>
              {confirmando
                ? "Você já está logado. Confira a conta e continue para o pagamento."
                : TITLES[mode].s}
            </p>
          </div>

          {notice && !confirmando && (
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

          {confirmando && (
            <div style={{ display: "grid", gap: 12, marginBottom: 4 }}>
              <div
                className="card"
                style={{ padding: "14px 16px", display: "grid", gap: 2 }}
              >
                <span className="tag-mono subtle">Você está logado como</span>
                <span style={{ fontWeight: 600 }}>{aluno?.email}</span>
              </div>
              <Button
                type="button"
                variant="primary"
                size="lg"
                block
                icon={busy ? undefined : "arrow"}
                disabled={busy}
                onClick={continuarComoLogado}
              >
                {busy ? "Aguarde..." : "Continuar e ir para o pagamento"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="lg"
                block
                icon="users"
                disabled={busy}
                onClick={entrarOutraConta}
              >
                Entrar com outra conta
              </Button>
            </div>
          )}

          {!confirmando && (
            <>
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
                </div>
                {mode === "signup" && (
                  <div className="field">
                    <label htmlFor="au-zap">WhatsApp</label>
                    <div className="input-group">
                      <span className="ico">
                        <Icon name="whatsapp" size={17} />
                      </span>
                      <input
                        id="au-zap"
                        className="input"
                        type="tel"
                        inputMode="tel"
                        placeholder="(51) 99999-9999"
                        value={telefone}
                        onChange={(e) => setTelefone(e.target.value)}
                      />
                    </div>
                  </div>
                )}
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
                        type={showSenha ? "text" : "password"}
                        placeholder="••••••••"
                        value={senha}
                        onChange={(e) => setSenha(e.target.value)}
                        style={{ paddingRight: 42 }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowSenha((v) => !v)}
                        aria-pressed={showSenha}
                        aria-label={
                          showSenha ? "Ocultar senha" : "Mostrar senha"
                        }
                        title={showSenha ? "Ocultar senha" : "Mostrar senha"}
                        style={{
                          position: "absolute",
                          right: 10,
                          top: "50%",
                          transform: "translateY(-50%)",
                          background: "none",
                          border: 0,
                          cursor: "pointer",
                          color: "var(--text-subtle)",
                          display: "grid",
                          placeItems: "center",
                          padding: 4,
                        }}
                      >
                        <Icon name={showSenha ? "eyeOff" : "eye"} size={18} />
                      </button>
                    </div>
                    {mode === "signup" && (
                      <span
                        className="tag-mono subtle"
                        style={{
                          lineHeight: 1.4,
                          color:
                            senha.length === 0
                              ? undefined
                              : senha.length >= SENHA_MIN
                                ? "var(--success)"
                                : "var(--danger)",
                        }}
                      >
                        {senha.length >= SENHA_MIN
                          ? "✓ Tamanho de senha válido"
                          : "Use no mínimo 8 caracteres."}
                      </span>
                    )}
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
            </>
          )}
        </form>
      </div>
    </div>
  );
}
