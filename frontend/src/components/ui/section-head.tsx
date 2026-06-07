export interface SectionHeadProps {
  eyebrow: string;
  title: string;
  sub?: string;
  center?: boolean;
}

export function SectionHead({ eyebrow, title, sub, center }: SectionHeadProps) {
  return (
    <div
      style={{
        maxWidth: center ? 680 : 760,
        margin: center ? "0 auto 48px" : "0 0 44px",
        textAlign: center ? "center" : "left",
      }}
    >
      <div
        className="eyebrow"
        style={{ marginBottom: 14, color: "var(--primary)" }}
      >
        // {eyebrow}
      </div>
      <h2 style={{ fontSize: "2.5rem", marginBottom: 16 }}>{title}</h2>
      {sub && (
        <p className="muted" style={{ fontSize: "1.08rem", lineHeight: 1.55 }}>
          {sub}
        </p>
      )}
    </div>
  );
}
