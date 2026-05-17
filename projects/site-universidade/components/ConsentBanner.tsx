"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "consent_analytics";

type ConsentValue = "granted" | "denied";
type GtagConsentCommand = "consent";
type GtagConsentAction = "update";

declare global {
  interface Window {
    gtag?: (
      command: GtagConsentCommand,
      action: GtagConsentAction,
      consent: {
        analytics_storage: ConsentValue;
        ad_storage: ConsentValue;
        ad_user_data: ConsentValue;
        ad_personalization: ConsentValue;
      }
    ) => void;
  }
}

function applyConsent(value: ConsentValue) {
  if (typeof window === "undefined" || typeof window.gtag !== "function") return;
  window.gtag("consent", "update", {
    analytics_storage: value,
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
  });
}

export function ConsentBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as ConsentValue | null;
    if (stored) {
      applyConsent(stored);
    } else {
      setVisible(true);
    }
  }, []);

  function accept() {
    localStorage.setItem(STORAGE_KEY, "granted");
    applyConsent("granted");
    setVisible(false);
  }

  function reject() {
    localStorage.setItem(STORAGE_KEY, "denied");
    applyConsent("denied");
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 sm:p-6">
      <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-5 shadow-lg sm:flex sm:items-center sm:gap-6">
        <p className="flex-1 text-sm text-slate-600">
          Utilizamos cookies de análise para melhorar o site.{" "}
          <a href="/privacidade/" className="underline hover:text-brand-700">
            Política de privacidade
          </a>
        </p>
        <div className="mt-4 flex shrink-0 gap-3 sm:mt-0">
          <button
            onClick={reject}
            className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-400 hover:text-slate-900"
          >
            Rejeitar
          </button>
          <button
            onClick={accept}
            className="rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900"
          >
            Aceitar
          </button>
        </div>
      </div>
    </div>
  );
}
