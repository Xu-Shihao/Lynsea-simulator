"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";
import { ResultsView } from "../../../components/ResultsView";
import { sampleResult } from "../../../lib/sampleResult";
import { DEMO_STORAGE_KEY } from "../../../lib/storage";
import type { SimResult } from "../../../lib/types";

// Client half of the /sim/[id] route. The `id` is resolved by the server
// component (so the route can be statically exported); everything below stays
// client-side — SSE streaming for a live sim, or the bundled fixture for demos.
export function SimClient({ id }: { id: string }) {
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
