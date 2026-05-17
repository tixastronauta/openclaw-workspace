import { getAllCourses, getAllDistricts, getAllFaculties, getAllUniversities, getCycles, getAreas, getDuracoes, getTiposEnsino, getAllProvasIngresso, getAllProvaSets } from "@/lib/courses";
import { getTop10Metrics } from "@/lib/top10";
import { slugify } from "@/lib/slug";
import { siteConfig } from "@/lib/site";

export const dynamic = "force-static";

export function GET() {
  const staticRoutes = ["", "/cursos", "/faculdades", "/universidades", "/ciclos", "/distritos", "/areas", "/duracoes", "/tipos-ensino", "/provas-ingresso", "/top-10-cursos", "/quem-somos", "/privacidade", "/termos"];
  const top10Routes = getTop10Metrics().map((m) => `/top-10-cursos/${m.id}`);
  const courseRoutes = getAllCourses().map((course) => `/cursos/${course.slug}`);
  const facultyRoutes = getAllFaculties().map((faculty) => `/faculdades/${faculty.slug}`);
  const universityRoutes = getAllUniversities().map((university) => `/universidades/${university.slug}`);
  const cycleRoutes = getCycles().map((cycle) => `/ciclos/${slugify(cycle)}`);
  const districtRoutes = getAllDistricts().map((district) => `/distritos/${district.slug}`);
  const areaRoutes = getAreas().map((area) => `/areas/${slugify(area)}`);
  const duracaoRoutes = getDuracoes().map((d) => `/duracoes/${slugify(d)}`);
  const tipoEnsinoRoutes = getTiposEnsino().map((t) => `/tipos-ensino/${slugify(t)}`);
  const provaIngressoRoutes = getAllProvasIngresso().map((p) => `/provas-ingresso/${slugify(p.name)}`);
  const provaSetRoutes = getAllProvaSets().map((s) => `/provas-ingresso/conjunto/${s.slug}`);
  const urls = [...staticRoutes, ...top10Routes, ...courseRoutes, ...facultyRoutes, ...universityRoutes, ...cycleRoutes, ...districtRoutes, ...areaRoutes, ...duracaoRoutes, ...tipoEnsinoRoutes, ...provaIngressoRoutes, ...provaSetRoutes]
    .map((route) => `  <url><loc>${siteConfig.url}${route}/</loc></url>`)
    .join("\n");

  return new Response(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>`, {
    headers: { "Content-Type": "application/xml" }
  });
}
