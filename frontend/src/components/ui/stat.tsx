export interface StatProps {
  value: string;
  label: string;
  accent?: boolean;
}

export function Stat({ value, label, accent }: StatProps) {
  return (
    <div className="flex col" style={{ gap: 2 }}>
      <span
        className="price"
        style={{
          fontSize: "2rem",
          color: accent ? "var(--primary)" : "var(--text)",
        }}
      >
        {value}
      </span>
      <span className="tag-mono">{label}</span>
    </div>
  );
}
