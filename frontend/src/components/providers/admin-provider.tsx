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
  adminLogout as apiAdminLogout,
  getAdminMe,
  getAdminToken,
  type AdminMe,
} from "@/lib/admin-api";

type Status = "loading" | "authed" | "unauthed";

interface AdminContextValue {
  status: Status;
  admin: AdminMe | null;
  refresh: () => void;
  logout: () => void;
}

const AdminContext = createContext<AdminContextValue>({
  status: "loading",
  admin: null,
  refresh: () => {},
  logout: () => {},
});

export function useAdmin() {
  return useContext(AdminContext);
}

export function AdminProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [admin, setAdmin] = useState<AdminMe | null>(null);

  const load = useCallback(() => {
    if (!getAdminToken()) {
      setStatus("unauthed");
      return;
    }
    getAdminMe()
      .then((a) => {
        setAdmin(a);
        setStatus("authed");
      })
      .catch(() => {
        setAdmin(null);
        setStatus("unauthed");
      });
  }, []);

  useEffect(() => load(), [load]);

  const logout = useCallback(() => {
    // fire-and-forget: a revogação server-side é best-effort; a UI desloga já.
    // (adminLogout captura o token de forma síncrona antes de qualquer await.)
    void apiAdminLogout();
    setAdmin(null);
    setStatus("unauthed");
  }, []);

  return (
    <AdminContext.Provider value={{ status, admin, refresh: load, logout }}>
      {children}
    </AdminContext.Provider>
  );
}
