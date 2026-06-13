import type { MetadataRoute } from "next";

/** /manifest.webmanifest — identidade do site no navegador (ícone instalável,
 *  cor da barra). Ícones gerados por scripts/gen-favicons.mjs. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "RödelCar — Câmbios e Cursos",
    short_name: "RödelCar",
    description:
      "Câmbio automático e automatizado em Canoas-RS e cursos online para mecânicos.",
    start_url: "/",
    display: "standalone",
    background_color: "#0a0c10",
    theme_color: "#e5372b",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      {
        src: "/icons/maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
