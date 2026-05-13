import type { Metadata } from "next";
import { Suspense } from "react";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { SearchResultsClient } from "./SearchResultsClient";

export const metadata: Metadata = {
  title: "Pesquisa",
  robots: { index: false },
};

export default function SearchPage() {
  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Pesquisa" }]} />
      <Suspense>
        <SearchResultsClient />
      </Suspense>
    </Container>
  );
}
