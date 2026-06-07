import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RödelCar",
  description: "Portal e plataforma de cursos RödelCar Câmbios",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
