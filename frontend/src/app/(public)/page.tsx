import { Hero } from "@/components/portal/hero";
import { SocialProof } from "@/components/portal/social-proof";
import { Vitrine } from "@/components/portal/vitrine";
import { getCursos, getDepoimentos, getVideos } from "@/lib/api";

export default async function HomePage() {
  const [courses, testimonials, videos] = await Promise.all([
    getCursos(),
    getDepoimentos(),
    getVideos(),
  ]);
  return (
    <main>
      <Hero />
      <SocialProof testimonials={testimonials} videos={videos} />
      <Vitrine courses={courses} />
    </main>
  );
}
