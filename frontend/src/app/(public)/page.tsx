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
  return (
    <main>
      <Hero />
      <SocialProof
        testimonials={testimonials}
        videos={videos}
        google={google}
      />
      <Turmas photos={turmas.length ? turmas : undefined} />
      <Vitrine courses={courses} planos={planos} />
    </main>
  );
}
