"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchSimulation, openSimulationStream } from "./api";
import type {
  BranchPoint,
  CredibilityCard,
  MetricPoint,
  Persona,
  Recommendation,
  SimResult,
  StatusEvent,
  TimelineEvent,
} from "./types";

export interface SimState {
  decision: string;
  options: [string, string] | null;
  personas: Persona[];
  events: TimelineEvent[];
  metrics: MetricPoint[];
  branchPoints: BranchPoint[];
  credibility: CredibilityCard | null;
  recommendation: Recommendation | null;
  status: StatusEvent | null;
  done: boolean;
  error: string | null;
  /** true while connecting/streaming and not yet done or errored */
  loading: boolean;
}

const EMPTY: SimState = {
  decision: "",
  options: null,
  personas: [],
  events: [],
  metrics: [],
  branchPoints: [],
  credibility: null,
  recommendation: null,
  status: null,
  done: false,
  error: null,
  loading: true,
};

function fromResult(r: SimResult): SimState {
  return {
    decision: r.decision,
    options: r.options,
    personas: r.personas,
    events: r.events,
    metrics: r.metrics,
    branchPoints: r.branch_points,
    credibility: r.credibility,
    recommendation: r.recommendation,
    status: { phase: "done", message: "Loaded", progress: 1 },
    done: true,
    error: null,
    loading: false,
  };
}

/** dedupe-merge helper keyed by id */
function upsertById<T extends { id: string }>(arr: T[], item: T): T[] {
  const i = arr.findIndex((x) => x.id === item.id);
  if (i === -1) return [...arr, item];
  const next = arr.slice();
  next[i] = item;
  return next;
}

/** dedupe-merge metrics keyed by branch+month */
function upsertMetric(arr: MetricPoint[], item: MetricPoint): MetricPoint[] {
  const i = arr.findIndex(
    (x) => x.branch === item.branch && x.month === item.month,
  );
  if (i === -1) return [...arr, item];
  const next = arr.slice();
  next[i] = item;
  return next;
}

interface UseSimStreamArgs {
  simId: string;
  /** if provided, render this static result instead of streaming (demo mode) */
  staticResult?: SimResult | null;
  /** known decision/options to seed the header before stream data arrives */
  seed?: { decision?: string; options?: [string, string] };
}

export function useSimStream({
  simId,
  staticResult,
  seed,
}: UseSimStreamArgs): SimState & { retry: () => void } {
  const [state, setState] = useState<SimState>(() => {
    if (staticResult) return fromResult(staticResult);
    return {
      ...EMPTY,
      decision: seed?.decision ?? "",
      options: seed?.options ?? null,
    };
  });
  const [attempt, setAttempt] = useState(0);
  const disposerRef = useRef<(() => void) | null>(null);

  const retry = useCallback(() => {
    setState((s) => ({ ...EMPTY, decision: s.decision, options: s.options }));
    setAttempt((a) => a + 1);
  }, []);

  useEffect(() => {
    if (staticResult) {
      setState(fromResult(staticResult));
      return;
    }
    let cancelled = false;

    setState((s) => ({
      ...EMPTY,
      decision: s.decision || seed?.decision || "",
      options: s.options ?? seed?.options ?? null,
    }));

    const dispose = openSimulationStream(simId, {
      onStatus: (st) =>
        setState((s) => (cancelled ? s : { ...s, status: st })),
      onPersona: (p) =>
        setState((s) =>
          cancelled ? s : { ...s, personas: upsertById(s.personas, p) },
        ),
      onTimelineEvent: (e) =>
        setState((s) =>
          cancelled ? s : { ...s, events: upsertById(s.events, e) },
        ),
      onMetric: (m) =>
        setState((s) =>
          cancelled ? s : { ...s, metrics: upsertMetric(s.metrics, m) },
        ),
      onBranchPoint: (b) =>
        setState((s) =>
          cancelled ? s : { ...s, branchPoints: [...s.branchPoints, b] },
        ),
      onCredibility: (c) =>
        setState((s) => (cancelled ? s : { ...s, credibility: c })),
      onRecommendation: (r) =>
        setState((s) => (cancelled ? s : { ...s, recommendation: r })),
      onDone: () =>
        setState((s) =>
          cancelled
            ? s
            : {
                ...s,
                done: true,
                loading: false,
                status: s.status ?? {
                  phase: "done",
                  message: "Complete",
                  progress: 1,
                },
              },
        ),
      onError: (message) => {
        if (cancelled) return;
        // Stream failed. Attempt a one-shot GET in case the sim already
        // finished server-side; otherwise surface the error for retry.
        fetchSimulation(simId)
          .then((r) => {
            if (!cancelled) setState(fromResult(r));
          })
          .catch(() => {
            if (!cancelled)
              setState((s) => ({ ...s, error: message, loading: false }));
          });
      },
    });

    disposerRef.current = dispose;
    return () => {
      cancelled = true;
      dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [simId, staticResult, attempt]);

  return { ...state, retry };
}
