"use client";

import { useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { PortalContext, type ToastData } from "./portal-context";
import { Header } from "./header";
import { Footer } from "./footer";
import { ScheduleDialog } from "./schedule-dialog";
import { Toast } from "./toast";

export function PortalChrome({ children }: { children: ReactNode }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);

  const openSchedule = useCallback(() => setDialogOpen(true), []);
  const showToast = useCallback((t: ToastData) => setToast(t), []);

  const value = useMemo(
    () => ({ openSchedule, showToast }),
    [openSchedule, showToast],
  );

  const scheduleDone = () => {
    setDialogOpen(false);
    setToast({
      title: "Agendamento confirmado",
      msg: "Enviaremos a confirmação no WhatsApp",
    });
  };

  return (
    <PortalContext.Provider value={value}>
      <Header />
      {children}
      <Footer />
      <ScheduleDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onDone={scheduleDone}
      />
      {toast && (
        <Toast
          title={toast.title}
          msg={toast.msg}
          onClose={() => setToast(null)}
        />
      )}
    </PortalContext.Provider>
  );
}
