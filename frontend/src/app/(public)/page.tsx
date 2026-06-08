import { Hero } from "@/components/portal/hero";
import { SocialProof } from "@/components/portal/social-proof";
import { Vitrine } from "@/components/portal/vitrine";
import { getCursos } from "@/lib/api";

export default async function HomePage() {
  const courses = await getCursos();
  return (
    <main>
      <Hero />
      <SocialProof />
      <Vitrine courses={courses} />
    </main>
  );
}
