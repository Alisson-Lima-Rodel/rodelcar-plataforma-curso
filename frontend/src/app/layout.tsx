import type { Metadata } from "next";
import { Archivo, Hanken_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/components/providers/query-provider";
import { AuthProvider } from "@/components/providers/auth-provider";

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
  metadataBase: new URL("https://rodelcar.com.br"),
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
      <body>
        <QueryProvider>
          <AuthProvider>{children}</AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
