import type { Metadata } from "next";
import Script from "next/script";
import { Suspense } from "react";
import "./globals.css";
import { ConsentBanner } from "@/components/ConsentBanner";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { NavigationLoader } from "@/components/NavigationLoader";
import { PageTransition } from "@/components/PageTransition";
import { siteConfig } from "@/lib/site";

const GTM_ID = process.env.NEXT_PUBLIC_GTM_ID;

const ogImage = {
  url: "/og/og-1200x630.png",
  width: 1200,
  height: 630,
  alt: "Universidade.pt"
};

export const metadata: Metadata = {
  metadataBase: new URL(siteConfig.url),
  title: {
    default: `${siteConfig.name} — cursos do ensino superior em Portugal`,
    template: `%s | ${siteConfig.name}`
  },
  description: siteConfig.description,
  manifest: "/site.webmanifest",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" }
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }]
  },
  openGraph: {
    type: "website",
    locale: "pt_PT",
    url: siteConfig.url,
    siteName: siteConfig.name,
    title: `${siteConfig.name} — cursos do ensino superior em Portugal`,
    description: siteConfig.description,
    images: [ogImage]
  },
  twitter: {
    card: "summary_large_image",
    title: `${siteConfig.name} — cursos do ensino superior em Portugal`,
    description: siteConfig.description,
    images: [ogImage.url]
  },
  alternates: {
    canonical: "/"
  }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-PT">
      <head>
        {/* Consent Mode v2 defaults must be set before GTM loads */}
        <script dangerouslySetInnerHTML={{ __html:
          `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('consent','default',{analytics_storage:'denied',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',wait_for_update:500});`
        }} />
      </head>
      <body className="min-h-screen antialiased">
        {GTM_ID && (
          <>
            <Script
              id="gtm-script"
              strategy="afterInteractive"
              dangerouslySetInnerHTML={{
                __html: `(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);})(window,document,'script','dataLayer','${GTM_ID}');`
              }}
            />
            <noscript>
              <iframe
                src={`https://www.googletagmanager.com/ns.html?id=${GTM_ID}`}
                height="0"
                width="0"
                style={{ display: "none", visibility: "hidden" }}
              />
            </noscript>
          </>
        )}
        <Suspense fallback={null}>
          <NavigationLoader />
        </Suspense>
        <Header />
        <main>
          <Suspense fallback={children}>
            <PageTransition>{children}</PageTransition>
          </Suspense>
        </main>
        <Footer />
        <ConsentBanner />
      </body>
    </html>
  );
}
