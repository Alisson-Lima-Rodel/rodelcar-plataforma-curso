"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Stars } from "@/components/ui/stars";
import { Reveal } from "@/components/ui/reveal";
import { SectionHead } from "@/components/ui/section-head";
import { BRAND, type Testimonial, type Video } from "@/lib/portal-data";
import { youtubeThumb } from "@/lib/youtube";

export function SocialProof({
  testimonials = [],
  videos = [],
}: {
  testimonials?: Testimonial[];
  videos?: Video[];
}) {
  const [idx, setIdx] = useState(0);
  const t = testimonials;
  const safeIdx = t.length ? idx % t.length : 0;
  const go = (d: number) => setIdx((safeIdx + d + t.length) % t.length);

  return (
    <section
      id="prova"
      className="section"
      style={{
        background: "var(--surface)",
        borderTop: "1px solid var(--border)",
        borderBottom: "1px solid var(--border)",
        scrollMarginTop: 80,
      }}
    >
      <div className="wrap">
        <SectionHead
          eyebrow="Prova de quem entende"
          title="Resultados que falam por nós"
          sub="Conteúdo aberto no YouTube e a palavra de quem aplicou o método na própria bancada."
        />

        {/* Video grid */}
        {videos.length > 0 && (
          <Reveal
            stagger
            className="social-videos"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 22,
              marginBottom: 18,
            }}
          >
            {videos.map((v, i) => {
              const capa = youtubeThumb(v.url);
              return (
                <a
                  key={i}
                  href={v.url || BRAND.youtube}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="video-card card card-hover"
                  style={{
                    padding: 12,
                    cursor: "pointer",
                    textDecoration: "none",
                    color: "inherit",
                    display: "block",
                  }}
                >
                  <div
                    className="thumb"
                    style={{
                      marginBottom: 13,
                      ...(capa
                        ? {
                            backgroundImage: `url(${capa})`,
                            backgroundSize: "cover",
                            backgroundPosition: "center",
                          }
                        : {}),
                    }}
                  >
                    <div className="play-btn">
                      <Icon name="play" size={20} />
                    </div>
                    <span
                      className="badge"
                      style={{
                        position: "absolute",
                        top: 9,
                        right: 9,
                        padding: "3px 8px",
                        background: "rgba(10,12,16,0.8)",
                        borderColor: "var(--border-strong)",
                      }}
                    >
                      {v.dur}
                    </span>
                    {!capa && (
                      <span className="thumb-label">[ youtube · 16:9 ]</span>
                    )}
                  </div>
                  <div style={{ padding: "0 4px 6px" }}>
                    <p
                      style={{
                        fontWeight: 600,
                        fontSize: "0.98rem",
                        marginBottom: 7,
                        lineHeight: 1.3,
                      }}
                    >
                      {v.t}
                    </p>
                    <span className="tag-mono">
                      {v.views ? `${v.views} de visualizações` : "YouTube"}
                    </span>
                  </div>
                </a>
              );
            })}
          </Reveal>
        )}
        <div style={{ textAlign: "center", marginBottom: 64 }}>
          <Button variant="link" iconRight="arrow" href={BRAND.youtube}>
            Ver o canal completo no YouTube
          </Button>
        </div>

        {/* Testimonials carousel */}
        {t.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr",
              maxWidth: 860,
              margin: "0 auto",
            }}
          >
            <div
              className="card"
              style={{
                padding: "40px 44px",
                position: "relative",
                background: "var(--surface-2)",
              }}
            >
              <Icon
                name="message"
                size={26}
                style={{
                  color: "var(--primary)",
                  opacity: 0.4,
                  marginBottom: 16,
                }}
              />
              <div style={{ minHeight: 132 }}>
                <Stars value={t[safeIdx].stars} size={19} />
                <p
                  key={idx}
                  style={{
                    fontSize: "1.32rem",
                    lineHeight: 1.5,
                    margin: "16px 0 24px",
                    fontFamily: "var(--font-display)",
                    fontWeight: 500,
                    letterSpacing: "-0.01em",
                    animation: "fade 320ms ease-out",
                  }}
                >
                  &ldquo;{t[safeIdx].text}&rdquo;
                </p>
                <div className="flex center gap-3">
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 9999,
                      background: "linear-gradient(135deg,#2a2f3a,#171a21)",
                      border: "1px solid var(--border-strong)",
                      display: "grid",
                      placeItems: "center",
                      fontFamily: "var(--font-display)",
                      fontWeight: 800,
                      color: "var(--text-muted)",
                    }}
                  >
                    {t[safeIdx].name
                      .split(" ")
                      .map((n) => n[0])
                      .slice(0, 2)
                      .join("")}
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.98rem" }}>
                      {t[safeIdx].name}
                    </div>
                    <div className="tag-mono">{t[safeIdx].role}</div>
                  </div>
                </div>
              </div>
              {/* controls */}
              <div
                className="flex center between"
                style={{
                  marginTop: 28,
                  paddingTop: 22,
                  borderTop: "1px solid var(--border)",
                }}
              >
                <div className="flex center gap-2">
                  {t.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setIdx(i)}
                      aria-label={`Depoimento ${i + 1}`}
                      style={{
                        width: i === safeIdx ? 22 : 8,
                        height: 8,
                        borderRadius: 9999,
                        border: 0,
                        cursor: "pointer",
                        background:
                          i === safeIdx
                            ? "var(--primary)"
                            : "var(--border-strong)",
                        transition: "all 200ms ease-out",
                      }}
                    />
                  ))}
                </div>
                <div className="flex center gap-2">
                  <button
                    onClick={() => go(-1)}
                    className="btn btn-secondary btn-sm"
                    style={{ width: 40, padding: 0, height: 40 }}
                    aria-label="Anterior"
                  >
                    <Icon name="arrowLeft" size={18} />
                  </button>
                  <button
                    onClick={() => go(1)}
                    className="btn btn-secondary btn-sm"
                    style={{ width: 40, padding: 0, height: 40 }}
                    aria-label="Próximo"
                  >
                    <Icon name="arrow" size={18} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
