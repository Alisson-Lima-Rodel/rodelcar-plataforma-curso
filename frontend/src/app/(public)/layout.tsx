import type { ReactNode } from "react";
import { PortalChrome } from "@/components/portal/portal-chrome";
import { JsonLd } from "@/components/seo/json-ld";
import { ORG_JSONLD, WEBSITE_JSONLD } from "@/lib/seo";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <PortalChrome>
      <JsonLd data={ORG_JSONLD} />
      <JsonLd data={WEBSITE_JSONLD} />
      {children}
    </PortalChrome>
  );
}
