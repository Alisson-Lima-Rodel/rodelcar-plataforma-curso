"use client";

import { useEffect } from "react";
import { Icon } from "@/components/ui/icon";

export interface ToastProps {
  msg: string;
  title?: string;
  onClose: () => void;
}

export function Toast({ msg, title = "Tudo certo", onClose }: ToastProps) {
  useEffect(() => {
    const t = setTimeout(onClose, 4200);
    return () => clearTimeout(t);
  }, [onClose]);
  return (
    <div className="toast" role="status" aria-live="polite">
      <Icon
        name="checkCircle"
        size={22}
        style={{ color: "var(--success)", flexShrink: 0 }}
      />
      <div>
        <div style={{ fontWeight: 600, fontSize: "0.92rem" }}>{title}</div>
        <div className="tag-mono" style={{ marginTop: 2 }}>
          {msg}
        </div>
      </div>
      <button
        onClick={onClose}
        className="btn btn-ghost"
        style={{ width: 30, height: 30, padding: 0, marginLeft: 6 }}
        aria-label="Fechar"
      >
        <Icon name="x" size={15} />
      </button>
    </div>
  );
}
