import type { Metadata } from "next";
import { Hero } from "@/components/portal/hero";
import { SocialProof } from "@/components/portal/social-proof";
import { Turmas } from "@/components/portal/turmas";
import { Vitrine } from "@/components/portal/vitrine";
import {
  getCursos,
  getDepoimentos,
  getGoogleReviews,
  getPlanos,
  getTurmasMidia,
  getVideos,
} from "@/lib/api";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

export default async function HomePage() {
  const [courses, testimonials, videos, planos, google, turmas] =
    await Promise.all([
      getCursos(),
      getDepoimentos(),
      getVideos(),
      getPlanos(),
      getGoogleReviews(),
      getTurmasMidia(),
    ]);
  // Card Premium vende a assinatura anual (acesso total ao catálogo).
  const planoAnual =
    planos.find((p) => p.intervalo === "anual") ?? planos[0] ?? null;
  return (
    <main>
      <Hero />
      <SocialProof
        testimonials={testimonials}
        videos={videos}
        google={google}
      />
      <Turmas photos={turmas.length ? turmas : undefined} />
      <Vitrine courses={courses} planoAnual={planoAnual} />
    </main>
  );
}
