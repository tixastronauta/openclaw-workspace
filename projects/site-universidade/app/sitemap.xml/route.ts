import { getAllCourses, getAllFaculties } from "@/lib/courses";
import { siteConfig } from "@/lib/site";

export const dynamic = "force-static";

export function GET() {
  const staticRoutes = ["", "/cursos", "/faculdades", "/sobre", "/contacto", "/privacidade", "/termos", "/fontes-oficiais"];
  const courseRoutes = getAllCourses().map((course) => `/cursos/${course.slug}`);
  const facultyRoutes = getAllFaculties().map((faculty) => `/faculdades/${faculty.slug}`);
  const urls = [...staticRoutes, ...courseRoutes, ...facultyRoutes]
    .map((route) => `  <url><loc>${siteConfig.url}${route}/</loc></url>`)
    .join("\n");

  return new Response(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>`, {
    headers: { "Content-Type": "application/xml" }
  });
}
