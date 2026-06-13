import { ImageResponse } from "next/og";

/* Cartão padrão de compartilhamento (og:image) — gerado no build.
   Páginas de curso com capa própria sobrescrevem via generateMetadata. */

export const alt =
  "RödelCar — Câmbio automático e automatizado · Cursos para mecânicos";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** Archivo Black itálico (a fonte do wordmark), buscada no build; se a rede
 *  falhar, o cartão sai com a fonte padrão — nunca quebra a página. */
async function fonteArchivo(): Promise<ArrayBuffer | null> {
  try {
    const css = await fetch(
      "https://fonts.googleapis.com/css2?family=Archivo:ital,wght@1,900",
      { headers: { "User-Agent": "Mozilla/5.0" } },
    ).then((r) => r.text());
    const url = css.match(/url\((https:[^)]+\.ttf)\)/)?.[1];
    if (!url) return null;
    return await fetch(url).then((r) => r.arrayBuffer());
  } catch {
    return null;
  }
}

export default async function OgImage() {
  const fonte = await fonteArchivo();
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "0 96px",
        backgroundColor: "#0a0c10",
        backgroundImage:
          "radial-gradient(circle at 85% 20%, rgba(229,55,43,0.28), rgba(10,12,16,0))",
        color: "#ffffff",
        fontFamily: fonte ? "Archivo" : "sans-serif",
      }}
    >
      <div
        style={{
          display: "flex",
          width: 120,
          height: 8,
          background: "#e5372b",
          borderRadius: 4,
          marginBottom: 36,
        }}
      />
      <div
        style={{
          display: "flex",
          fontSize: 110,
          fontWeight: 900,
          fontStyle: "italic",
          letterSpacing: "-0.04em",
        }}
      >
        <span style={{ color: "#ffffff" }}>Rodel</span>
        <span style={{ color: "#e5372b" }}>Car</span>
      </div>
      <div
        style={{
          display: "flex",
          fontSize: 34,
          marginTop: 18,
          color: "#c8ccd4",
        }}
      >
        Câmbios automáticos e automatizados · Cursos para mecânicos
      </div>
      <div
        style={{
          display: "flex",
          fontSize: 26,
          marginTop: 48,
          color: "#7d828c",
        }}
      >
        Canoas-RS · rodelcar.com.br
      </div>
    </div>,
    {
      ...size,
      fonts: fonte
        ? [{ name: "Archivo", data: fonte, style: "italic", weight: 900 }]
        : undefined,
    },
  );
}
