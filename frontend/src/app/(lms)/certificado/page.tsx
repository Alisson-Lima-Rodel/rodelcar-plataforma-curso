import type { Metadata } from "next";
import { Certificate } from "@/components/lms/certificate";

export const metadata: Metadata = { title: "Certificado" };

export default function CertificadoPage() {
  return <Certificate />;
}
