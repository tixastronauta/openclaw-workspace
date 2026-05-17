"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

function NavigationLoaderInner() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function startLoader() {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setLoading(true), 140);
    }

    function handleClick(e: MouseEvent) {
      const anchor = (e.target as HTMLElement).closest("a");
      if (!anchor || anchor.target === "_blank" || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) return;

      const target = new URL(href, window.location.href);
      if (target.origin !== window.location.origin) return;
      if (target.pathname === window.location.pathname && target.search === window.location.search) return;

      startLoader();
    }

    document.addEventListener("click", handleClick);
    document.addEventListener("navigation-start", startLoader);
    return () => {
      document.removeEventListener("click", handleClick);
      document.removeEventListener("navigation-start", startLoader);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setLoading(false);
  }, [pathname, searchParams]);

  if (!loading) return null;

  return (
    <div
      className="navigation-progress fixed left-0 right-0 top-0 z-[9999] h-0.5 bg-brand-600 shadow-[0_0_12px_rgba(37,99,235,0.45)]"
      aria-hidden="true"
    />
  );
}

export function NavigationLoader() {
  return <NavigationLoaderInner />;
}
