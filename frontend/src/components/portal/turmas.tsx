"use client";

import { useState, useEffect, useRef } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/ui/reveal";
import { SectionHead } from "@/components/ui/section-head";

type Photo = { src: string; span: "bento-wide" | "bento-tall"; alt: string };

// Fallback embutido (mídia em frontend/public/turmas/). Usado quando o backend
// ainda não tem mídias cadastradas — a seção nunca aparece vazia/quebrada.
// t1 virou a foto do hero; aqui ficam as 4 retrato (tiles altos, sem repetir).
const TURMA_PHOTOS: Photo[] = [
  {
    src: "/turmas/t2.jpg",
    span: "bento-tall",
    alt: "Turma reunida em volta da bancada durante a aula",
  },
  {
    src: "/turmas/t3.jpg",
    span: "bento-tall",
    alt: "Trem de engrenagens do câmbio sendo apresentado",
  },
  {
    src: "/turmas/t4.jpg",
    span: "bento-tall",
    alt: "Instrutor mostrando o conjunto eletrônico aos alunos",
  },
  {
    src: "/turmas/t5.jpg",
    span: "bento-tall",
    alt: "Prática em grupo na bancada",
  },
];

const VIDEO_SRC = "/turmas/turma.mp4";

function Lightbox({
  photos,
  index,
  onClose,
  onNav,
}: {
  photos: Photo[];
  index: number;
  onClose: () => void;
  onNav: (d: number) => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") onNav(1);
      if (e.key === "ArrowLeft") onNav(-1);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [index, onClose, onNav]);

  return (
    <div className="lightbox" onClick={onClose}>
      <button className="lb-btn lb-close" onClick={onClose} aria-label="Fechar">
        <Icon name="x" size={22} />
      </button>
      <button
        className="lb-btn lb-prev"
        onClick={(e) => {
          e.stopPropagation();
          onNav(-1);
        }}
        aria-label="Anterior"
      >
        <Icon name="arrowLeft" size={22} />
      </button>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={photos[index].src}
        alt={photos[index].alt}
        onClick={(e) => e.stopPropagation()}
      />
      <button
        className="lb-btn lb-next"
        onClick={(e) => {
          e.stopPropagation();
          onNav(1);
        }}
        aria-label="Próxima"
      >
        <Icon name="arrow" size={22} />
      </button>
      <span className="lb-count badge" onClick={(e) => e.stopPropagation()}>
        {index + 1} / {photos.length}
      </span>
    </div>
  );
}

export function Turmas({ photos = TURMA_PHOTOS }: { photos?: Photo[] }) {
  // `started` controla a troca poster→player; o "poster" é o 1º frame do vídeo.
  const [started, setStarted] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [lb, setLb] = useState(-1);
  const nav = (d: number) => setLb((lb + d + photos.length) % photos.length);

  const scrollToVitrine = () => {
    const el = document.getElementById("vitrine");
    if (el)
      window.scrollTo({
        top: el.getBoundingClientRect().top + window.scrollY - 70,
        behavior: "smooth",
      });
  };

  return (
    <section
      id="turmas"
      className="section"
      style={{ background: "var(--bg)", scrollMarginTop: 80 }}
    >
      <div className="wrap">
        <SectionHead
          eyebrow="Turmas presenciais"
          title="Aprendizado de bancada, na prática"
          sub="Turmas presenciais em Canoas-RS: mão na massa em câmbios reais, em grupos pequenos, com acompanhamento direto da equipe Rödelcar."
          center
        />

        {/* Vídeo em destaque — o "poster" é o 1º frame do próprio vídeo
            (preload="metadata" + fragmento #t=0.1 forçam o frame a renderizar). */}
        <Reveal
          className="turmas-video"
          style={{ maxWidth: 940, margin: "0 auto 18px" }}
        >
          <video
            ref={videoRef}
            src={`${VIDEO_SRC}#t=0.1`}
            controls={started}
            playsInline
            preload="metadata"
            onPlay={() => setStarted(true)}
          />
          {!started && (
            <div
              className="turmas-poster"
              onClick={() => videoRef.current?.play()}
            >
              <span className="turmas-play">
                <Icon name="play" size={30} />
              </span>
              <span
                className="badge"
                style={{
                  position: "absolute",
                  top: 16,
                  left: 16,
                  background: "rgba(10,12,16,0.8)",
                }}
              >
                <Icon name="bolt" size={12} /> Turma presencial · Canoas-RS
              </span>
            </div>
          )}
        </Reveal>

        <div
          className="flex center"
          style={{
            justifyContent: "center",
            gap: 22,
            marginBottom: 40,
            flexWrap: "wrap",
          }}
        >
          {(
            [
              ["Grupos reduzidos", "users"],
              ["Câmbios reais na bancada", "wrench"],
              ["Acompanhamento direto", "shield"],
            ] as const
          ).map(([t, ic]) => (
            <span
              key={t}
              className="flex center gap-2 tag-mono"
              style={{ color: "var(--text-muted)" }}
            >
              <Icon name={ic} size={15} style={{ color: "var(--primary)" }} />
              {t}
            </span>
          ))}
        </div>

        {/* Mosaico bento */}
        <Reveal className="bento">
          {photos.map((p, i) => (
            <div
              key={i}
              className={`bento-tile ${p.span}`}
              onClick={() => setLb(i)}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={p.src} alt={p.alt} loading="lazy" />
              <span className="bento-zoom">
                <Icon name="spark" size={16} />
              </span>
            </div>
          ))}
        </Reveal>

        <div style={{ textAlign: "center", marginTop: 32 }}>
          <span className="muted" style={{ fontSize: "0.95rem" }}>
            Quer estar na próxima turma presencial?{" "}
          </span>
          <Button variant="link" iconRight="arrow" onClick={scrollToVitrine}>
            Ver cursos e formação
          </Button>
        </div>
      </div>

      {lb >= 0 && (
        <Lightbox
          photos={photos}
          index={lb}
          onClose={() => setLb(-1)}
          onNav={nav}
        />
      )}
    </section>
  );
}

export type { Photo };
