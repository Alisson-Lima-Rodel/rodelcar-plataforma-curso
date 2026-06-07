import type { Metadata } from "next";
import type { ReactNode } from "react";
import "../lms.css";
import { LmsShell } from "@/components/lms/lms-shell";

export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function LmsLayout({ children }: { children: ReactNode }) {
  return <LmsShell>{children}</LmsShell>;
}
