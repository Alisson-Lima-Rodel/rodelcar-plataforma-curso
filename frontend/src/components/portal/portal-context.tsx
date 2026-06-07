"use client";

import { createContext, useContext } from "react";

export interface ToastData {
  title: string;
  msg: string;
}

export interface PortalContextValue {
  openSchedule: () => void;
  showToast: (t: ToastData) => void;
}

export const PortalContext = createContext<PortalContextValue>({
  openSchedule: () => {},
  showToast: () => {},
});

export function usePortal() {
  return useContext(PortalContext);
}
