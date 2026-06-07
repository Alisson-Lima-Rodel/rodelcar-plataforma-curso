"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { CourseCard } from "./course-card";
import type { Course } from "@/lib/portal-data";

export function CourseCarousel({ courses }: { courses: Course[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const update = () => {
    const el = ref.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 4);
  };

  useEffect(() => {
    update();
    const onR = () => update();
    window.addEventListener("resize", onR);
    return () => window.removeEventListener("resize", onR);
  }, []);

  const scroll = (dir: number) => {
    const el = ref.current;
    if (el)
      el.scrollBy({ left: dir * el.clientWidth * 0.85, behavior: "smooth" });
  };

  return (
    <div style={{ position: "relative" }}>
      <div ref={ref} className="carousel-row" onScroll={update}>
        {courses.map((c) => (
          <div key={c.id} className="carousel-item">
            <CourseCard c={c} />
          </div>
        ))}
      </div>
      <button
        className="carousel-arrow left"
        onClick={() => scroll(-1)}
        disabled={atStart}
        aria-label="Anterior"
      >
        <Icon name="arrowLeft" size={20} />
      </button>
      <button
        className="carousel-arrow right"
        onClick={() => scroll(1)}
        disabled={atEnd}
        aria-label="Próximos"
      >
        <Icon name="arrow" size={20} />
      </button>
    </div>
  );
}
