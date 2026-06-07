import { Icon } from "./icon";

export interface LogoProps {
  size?: "sm" | "md" | "lg";
  tagline?: boolean;
}

/** Wordmark "RodelCar" recriado em CSS (fiel ao logo da oficina): itálico
 *  pesado, "Rodel" claro + "Car" vermelho e o spark vermelho no canto. */
export function Logo({ size = "md", tagline = true }: LogoProps) {
  const W = { sm: "1.05rem", md: "1.32rem", lg: "2.1rem" }[size];
  const T = { sm: "0.4rem", md: "0.48rem", lg: "0.62rem" }[size];
  const sp = { sm: 8, md: 10, lg: 14 }[size];
  return (
    <span
      style={{
        display: "inline-flex",
        flexDirection: "column",
        gap: size === "lg" ? 6 : 4,
        lineHeight: 1,
      }}
    >
      <span
        style={{
          position: "relative",
          display: "inline-block",
          fontFamily: "var(--font-display)",
          fontWeight: 900,
          fontStyle: "italic",
          fontSize: W,
          letterSpacing: "-0.045em",
          whiteSpace: "nowrap",
          textShadow: "0 1px 0 rgba(0,0,0,0.45)",
        }}
      >
        <span style={{ color: "var(--text)" }}>Rodel</span>
        <span style={{ color: "var(--primary)" }}>Car</span>
        <span
          style={{
            position: "absolute",
            top: "-0.42em",
            right: "-0.55em",
            color: "var(--primary)",
            filter: "drop-shadow(0 0 5px rgba(229,55,43,0.6))",
          }}
        >
          <Icon name="sparkle4" size={sp} />
        </span>
      </span>
      {tagline && (
        <span
          style={{ display: "inline-flex", flexDirection: "column", gap: 3 }}
        >
          <span
            style={{
              height: 2,
              width: "100%",
              background:
                "linear-gradient(90deg, var(--primary) 60%, transparent)",
              borderRadius: 2,
            }}
          />
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: T,
              fontWeight: 500,
              letterSpacing: "0.16em",
              color: "var(--text-muted)",
              whiteSpace: "nowrap",
            }}
          >
            CÂMBIOS AUTOMÁTICOS E AUTOMATIZADOS
          </span>
        </span>
      )}
    </span>
  );
}
