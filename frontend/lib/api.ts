// API helpers for the Lynsea backend. The API base is read from
// NEXT_PUBLIC_API_BASE (default http://localhost:8000).

import type {
  BranchPoint,
  ClarificationPlan,
  CredibilityCard,
  Dimension,
  MetricPoint,
  Persona,
  Recommendation,
  SimResult,
  SimulateRequest,
  StatusEvent,
  TimelineEvent,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/**
 * fetch() wrapper that turns a network-level failure (backend offline, wrong
 * port, CORS blocked) — which surfaces as a bare `TypeError: Failed to fetch` —
 * into an actionable message instead of a cryptic one.
 */
async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new Error(
      `Can't reach the Lynsea backend at ${API_BASE}. Is it running? ` +
        `Start it with:  cd backend && .venv/bin/uvicorn app.main:app --port 8000  ` +
        `(or run ./demo.sh from the repo root). You can also click "Load demo" to ` +
        `explore a sample result offline.`,
    );
  }
}

/**
 * Create a simulation. Returns the sim_id.
 * Validates that exactly 2 options are provided (FROZEN contract).
 */
export async function createSimulation(
  req: SimulateRequest,
): Promise<{ sim_id: string }> {
  if (!req.options || req.options.length !== 2) {
    throw new Error("Exactly 2 options are required.");
  }
  const res = await apiFetch(`/api/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = await safeText(res);
    throw new Error(
      `Failed to start simulation (${res.status})${detail ? `: ${detail}` : ""}`,
    );
  }
  return (await res.json()) as { sim_id: string };
}

/**
 * Cancel an in-flight simulation (SYS-02 / FE-21).
 * POST {API_BASE}/api/simulate/{sim_id}/cancel. The server then emits an
 * `error` event on the open SSE stream, which the UI surfaces gracefully.
 */
export async function cancelSimulation(simId: string): Promise<void> {
  const res = await apiFetch(`/api/simulate/${simId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) {
    const detail = await safeText(res);
    throw new Error(
      `Failed to cancel simulation (${res.status})${detail ? `: ${detail}` : ""}`,
    );
  }
}

/** Fetch a complete, already-finished simulation (used for reload). */
export async function fetchSimulation(simId: string): Promise<SimResult> {
  const res = await apiFetch(`/api/simulate/${simId}`);
  if (!res.ok) {
    const detail = await safeText(res);
    throw new Error(
      `Failed to load simulation (${res.status})${detail ? `: ${detail}` : ""}`,
    );
  }
  return (await res.json()) as SimResult;
}

/**
 * Generate (or refine) a clarification plan for a decision (Phase 7 / FE-02).
 * Routed through `apiFetch` so a backend-down failure surfaces the same
 * actionable "is it running?" message as the other helpers. Pass `prior` + a
 * free-text `note` for an iterative refine round.
 */
export async function clarify(
  decision: string,
  prior?: ClarificationPlan | null,
  note?: string | null,
): Promise<ClarificationPlan> {
  const res = await apiFetch(`/api/clarify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, prior: prior ?? null, note: note ?? null }),
  });
  if (!res.ok) {
    const detail = await safeText(res);
    throw new Error(
      `Failed to refine the decision (${res.status})${detail ? `: ${detail}` : ""}`,
    );
  }
  return (await res.json()) as ClarificationPlan;
}

async function safeText(res: Response): Promise<string> {
  try {
    return (await res.text()).slice(0, 300);
  } catch {
    return "";
  }
}

// --- SSE streaming -----------------------------------------------------------

export interface StreamHandlers {
  onStatus?: (s: StatusEvent) => void;
  onPersona?: (p: Persona) => void;
  onDimensions?: (d: Dimension[]) => void;
  onTimelineEvent?: (e: TimelineEvent) => void;
  onMetric?: (m: MetricPoint) => void;
  onBranchPoint?: (b: BranchPoint) => void;
  onCredibility?: (c: CredibilityCard) => void;
  onRecommendation?: (r: Recommendation) => void;
  onDone?: (d: { sim_id: string }) => void;
  onError?: (message: string) => void;
}

/**
 * Open an EventSource against the SSE stream and dispatch named events to the
 * provided handlers. Returns a disposer that closes the connection.
 */
export function openSimulationStream(
  simId: string,
  handlers: StreamHandlers,
): () => void {
  const url = `${API_BASE}/api/simulate/${simId}/stream`;
  const es = new EventSource(url);
  let closed = false;

  const close = () => {
    if (!closed) {
      closed = true;
      es.close();
    }
  };

  const parse = <T,>(raw: string): T | null => {
    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  };

  es.addEventListener("status", (e) => {
    const d = parse<StatusEvent>((e as MessageEvent).data);
    if (d) handlers.onStatus?.(d);
  });
  es.addEventListener("persona", (e) => {
    const d = parse<Persona>((e as MessageEvent).data);
    if (d) handlers.onPersona?.(d);
  });
  es.addEventListener("dimensions", (e) => {
    const d = parse<{ dimensions: Dimension[] }>((e as MessageEvent).data);
    if (d?.dimensions) handlers.onDimensions?.(d.dimensions);
  });
  es.addEventListener("timeline_event", (e) => {
    const d = parse<TimelineEvent>((e as MessageEvent).data);
    if (d) handlers.onTimelineEvent?.(d);
  });
  es.addEventListener("metric", (e) => {
    const d = parse<MetricPoint>((e as MessageEvent).data);
    if (d) handlers.onMetric?.(d);
  });
  es.addEventListener("branch_point", (e) => {
    const d = parse<BranchPoint>((e as MessageEvent).data);
    if (d) handlers.onBranchPoint?.(d);
  });
  es.addEventListener("credibility", (e) => {
    const d = parse<CredibilityCard>((e as MessageEvent).data);
    if (d) handlers.onCredibility?.(d);
  });
  es.addEventListener("recommendation", (e) => {
    const d = parse<Recommendation>((e as MessageEvent).data);
    if (d) handlers.onRecommendation?.(d);
  });
  es.addEventListener("done", (e) => {
    const d = parse<{ sim_id: string }>((e as MessageEvent).data);
    handlers.onDone?.(d ?? { sim_id: simId });
    close();
  });
  es.addEventListener("error", (e) => {
    // Named "error" event from the server carries JSON. The generic
    // EventSource connection error has no data — surface a generic message.
    const data = (e as MessageEvent).data;
    if (typeof data === "string" && data.length) {
      const d = parse<{ message: string }>(data);
      handlers.onError?.(d?.message ?? "The simulation reported an error.");
    } else {
      handlers.onError?.(
        "Lost connection to the simulation stream. The backend may be offline.",
      );
    }
    close();
  });

  return close;
}
