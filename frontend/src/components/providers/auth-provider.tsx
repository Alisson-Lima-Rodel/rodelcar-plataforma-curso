"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  getAccessToken,
  getMe,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  type Me,
} from "@/lib/auth-api";

type Status = "loading" | "authed" | "unauthed";

interface AuthContextValue {
  status: Status;
  aluno: Me | null;
  login: (email: string, senha: string) => Promise<void>;
  register: (
    nome: string,
    email: string,
    senha: string,
    codigoIndicacao?: string | null,
  ) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  status: "loading",
  aluno: null,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [aluno, setAluno] = useState<Me | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      setStatus("unauthed");
      return;
    }
    getMe()
      .then((me) => {
        setAluno(me);
        setStatus("authed");
      })
      .catch(() => {
        setAluno(null);
        setStatus("unauthed");
      });
  }, []);

  const login = useCallback(async (email: string, senha: string) => {
    await apiLogin(email, senha);
    setAluno(await getMe());
    setStatus("authed");
  }, []);

  const register = useCallback(
    async (
      nome: string,
      email: string,
      senha: string,
      codigoIndicacao?: string | null,
    ) => {
      await apiRegister(nome, email, senha, codigoIndicacao);
      setAluno(await getMe());
      setStatus("authed");
    },
    [],
  );

  const logout = useCallback(async () => {
    await apiLogout();
    setAluno(null);
    setStatus("unauthed");
  }, []);

  return (
    <AuthContext.Provider value={{ status, aluno, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
