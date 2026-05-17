export const siteConfig = {
  name: "Universidade.pt",
  domain: "universidade.pt",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? process.env.CF_PAGES_URL ?? "https://universidade.pt",
  description: "Diretório independente de cursos do ensino superior em Portugal, com notas de entrada e ligações para fontes oficiais."
};
