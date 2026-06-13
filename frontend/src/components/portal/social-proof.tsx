"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Stars } from "@/components/ui/stars";
import { Reveal } from "@/components/ui/reveal";
import { SectionHead } from "@/components/ui/section-head";
import { BRAND, type Testimonial, type Video } from "@/lib/portal-data";
import { type GoogleReviews } from "@/lib/api";
import { youtubeThumb, youtubeWatchUrl } from "@/lib/youtube";

export function SocialProof({
  testimonials = [],
  videos = [],
  google,
}: {
  testimonials?: Testimonial[];
  videos?: Video[];
  google?: GoogleReviews;
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

        {/* Nota do Google (ficha da oficina) */}
        {google && google.total > 0 && google.rating != null && (
          <div
            className="card"
            style={{
              padding: "20px 24px",
              marginBottom: 26,
              display: "flex",
              gap: 22,
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <div style={{ textAlign: "center", minWidth: 96 }}>
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "2.6rem",
                  fontWeight: 800,
                  lineHeight: 1,
                  color: "var(--primary)",
                }}
              >
                {google.rating.toFixed(1)}
              </div>
              <Stars value={google.rating} size={15} />
              <div className="tag-mono subtle" style={{ marginTop: 6 }}>
                {google.total} avaliações no Google
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 240, display: "grid", gap: 8 }}>
              {google.reviews.slice(0, 2).map((r, i) => (
                <div key={i}>
                  <div
                    className="flex center gap-2"
                    style={{ marginBottom: 2 }}
                  >
                    <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                      {r.autor || "Cliente"}
                    </span>
                    {r.nota != null && <Stars value={r.nota} size={11} />}
                  </div>
                  {r.texto && (
                    <p
                      className="muted"
                      style={{
                        fontSize: "0.88rem",
                        lineHeight: 1.45,
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      }}
                    >
                      {r.texto}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

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
              // href reconstruído do id (nunca a string crua) — barra javascript:/data:
              const href = youtubeWatchUrl(v.url) || BRAND.youtube;
              return (
                <a
                  key={i}
                  href={href}
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
                    {v.estrelas ? (
                      <div style={{ marginBottom: 7 }}>
                        <Stars value={v.estrelas} size={14} />
                      </div>
                    ) : null}
                    <p
                      style={{
                        fontWeight: 600,
                        fontSize: "0.98rem",
                        marginBottom: 6,
                        lineHeight: 1.3,
                      }}
                    >
                      {v.t}
                    </p>
                    <div
                      className="flex center between"
                      style={{ gap: 8, flexWrap: "wrap" }}
                    >
                      <span className="tag-mono">{v.canal || "YouTube"}</span>
                      <span
                        className="flex center gap-1"
                        style={{
                          fontSize: "0.82rem",
                          fontWeight: 600,
                          color: "var(--primary)",
                        }}
                      >
                        Assistir
                        <Icon name="arrow" size={14} />
                      </span>
                    </div>
                    {(v.views || v.likes) && (
                      <div
                        className="flex center gap-3"
                        style={{ marginTop: 6 }}
                      >
                        {v.views && (
                          <span className="tag-mono subtle">
                            {v.views} views
                          </span>
                        )}
                        {v.likes && (
                          <span className="tag-mono subtle flex center gap-1">
                            <Icon name="thumbsUp" size={12} />
                            {v.likes}
                          </span>
                        )}
                      </div>
                    )}
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
