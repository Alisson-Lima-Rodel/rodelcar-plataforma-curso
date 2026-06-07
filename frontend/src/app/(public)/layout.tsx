import type { ReactNode } from "react";
import { PortalChrome } from "@/components/portal/portal-chrome";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return <PortalChrome>{children}</PortalChrome>;
}
