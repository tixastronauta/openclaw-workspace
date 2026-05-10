import { siteConfig } from "@/lib/site";

export const dynamic = "force-static";

export function GET() {
  return new Response(`User-agent: *\nAllow: /\nSitemap: ${siteConfig.url}/sitemap.xml\n`, {
    headers: { "Content-Type": "text/plain" }
  });
}
