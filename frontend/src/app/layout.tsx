import type { Metadata, Viewport } from "next";
import { Archivo, Hanken_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/components/providers/query-provider";
import { AuthProvider } from "@/components/providers/auth-provider";
import { SITE_URL } from "@/lib/seo";

const archivo = Archivo({
  subsets: ["latin"],
  weight: ["500", "600", "700", "800", "900"],
  variable: "--font-display",
  display: "swap",
});

const hanken = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: "RödelCar",
  title: {
    default: "RödelCar — Câmbio Automático e Automatizado · Canoas-RS",
    template: "%s · RödelCar",
  },
  description:
    "Especialista em câmbio automático e automatizado em Canoas-RS: Dualogic, PowerShift, iMotion, Easytronic e DSG. Diagnóstico de bancada e cursos para mecânicos.",
  keywords: [
    "câmbio automatizado",
    "Dualogic",
    "PowerShift",
    "DSG",
    "iMotion",
    "curso de câmbio",
    "Canoas RS",
  ],
  openGraph: {
    type: "website",
    locale: "pt_BR",
    siteName: "RödelCar",
    title: "RödelCar — Câmbio Automático e Automatizado",
    description:
      "Diagnóstico de bancada e formação técnica para mecânicos. Canoas-RS.",
  },
  twitter: { card: "summary_large_image" },
  // Token do Search Console (opcional, via env) — sem ele a tag não sai.
  verification: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION
    ? { google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION }
    : undefined,
};

export const viewport: Viewport = {
  themeColor: "#0a0c10",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="pt-BR"
      className={`${archivo.variable} ${hanken.variable} ${jetbrains.variable}`}
    >
      {/* suppressHydrationWarning: extensões do navegador (Grammarly, tradutor,
          gerenciadores de senha) injetam nós/atributos no body antes da hidratação
          e disparam "hydration failed" só em dev — isto evita o falso positivo. */}
      <body suppressHydrationWarning>
        <QueryProvider>
          <AuthProvider>{children}</AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
