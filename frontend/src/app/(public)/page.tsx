import type { Metadata } from "next";
import { Hero } from "@/components/portal/hero";
import { SocialProof } from "@/components/portal/social-proof";
import { Vitrine } from "@/components/portal/vitrine";
import {
  getCursos,
  getDepoimentos,
  getGoogleReviews,
  getPlanos,
  getVideos,
} from "@/lib/api";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

export default async function HomePage() {
  const [courses, testimonials, videos, planos, google] = await Promise.all([
    getCursos(),
    getDepoimentos(),
    getVideos(),
    getPlanos(),
    getGoogleReviews(),
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
      <Vitrine courses={courses} planoAnual={planoAnual} />
    </main>
  );
}
