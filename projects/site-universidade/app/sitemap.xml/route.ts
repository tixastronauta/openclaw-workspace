import { getAllCourses, getAllDistricts, getAllFaculties, getAllUniversities, getCycles } from "@/lib/courses";
import { slugify } from "@/lib/slug";
import { siteConfig } from "@/lib/site";

export const dynamic = "force-static";

export function GET() {
  const staticRoutes = ["", "/cursos", "/faculdades", "/universidades", "/ciclos", "/distritos", "/top-10", "/quem-somos", "/privacidade", "/termos", "/fontes-oficiais"];
  const courseRoutes = getAllCourses().map((course) => `/cursos/${course.slug}`);
  const facultyRoutes = getAllFaculties().map((faculty) => `/faculdades/${faculty.slug}`);
  const universityRoutes = getAllUniversities().map((university) => `/universidades/${university.slug}`);
  const cycleRoutes = getCycles().map((cycle) => `/ciclos/${slugify(cycle)}`);
  const districtRoutes = getAllDistricts().map((district) => `/distritos/${district.slug}`);
  const urls = [...staticRoutes, ...courseRoutes, ...facultyRoutes, ...universityRoutes, ...cycleRoutes, ...districtRoutes]
    .map((route) => `  <url><loc>${siteConfig.url}${route}/</loc></url>`)
    .join("\n");

  return new Response(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>`, {
    headers: { "Content-Type": "application/xml" }
  });
}
