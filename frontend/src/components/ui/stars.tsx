import { Icon } from "./icon";

export interface StarsProps {
  value?: number;
  size?: number;
}

export function Stars({ value = 5, size = 16 }: StarsProps) {
  return (
    <span className="stars">
      {[0, 1, 2, 3, 4].map((i) => (
        <Icon
          key={i}
          name="star"
          size={size}
          className={i < value ? "" : "empty"}
          style={{
            color:
              i < Math.round(value) ? "var(--primary)" : "var(--border-strong)",
          }}
        />
      ))}
    </span>
  );
}
