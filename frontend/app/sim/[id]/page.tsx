"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, use, useMemo } from "react";
import { ResultsView } from "../../../components/ResultsView";
import { sampleResult } from "../../../lib/sampleResult";
import { DEMO_STORAGE_KEY } from "../../../lib/storage";
import type { SimResult } from "../../../lib/types";

export default function SimPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return (
    <Suspense fallback={<LoadingFallback />}>
      <SimResults id={id} />
    </Suspense>
  );
}

function SimResults({ id }: { id: string }) {
  const searchParams = useSearchParams();
  const isDemo =
    searchParams.get("demo") === "1" || id === sampleResult.sim_id;

  // For the demo path, resolve a static result (sessionStorage handoff, then
  // the bundled fixture) so the page works fully offline.
  const staticResult: SimResult | null = useMemo(() => {
    if (!isDemo) return null;
    if (typeof window !== "undefined") {
      try {
        const raw = sessionStorage.getItem(DEMO_STORAGE_KEY);
        if (raw) return JSON.parse(raw) as SimResult;
      } catch {
        // fall through to bundled fixture
      }
    }
    return sampleResult;
  }, [isDemo]);

  return <ResultsView simId={id} staticResult={staticResult} />;
}

function LoadingFallback() {
  return (
    <main className="flex-1 grid place-items-center text-sm text-on-surface-variant">
      Loading simulation…
    </main>
  );
}
