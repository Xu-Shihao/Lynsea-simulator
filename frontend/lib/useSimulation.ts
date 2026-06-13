'use client';

/**
 * useSimulation.ts — SSE client hook
 *
 * Opens a Server-Sent Events stream from POST /api/simulate (or the mock),
 * reduces every incoming event into a typed SimulationState, and exposes
 * that state + a `start` function to consumer components.
 *
 * The hook signature is the API that FE-Dashboard and FE-Insight consume.
 * Do NOT change the returned interface shape without coordinating with those agents.
 */

import { useCallback, useReducer, useRef } from 'react';
import type {
  Branch,
  MetricPayload,
  SimulateRequest,
  SimulationState,
  SSEEventType,
  TimelineEventPayload,
} from './contract';
import { createMockStream } from './mockStream';

// ─── Initial state ────────────────────────────────────────────────────────────

function makeInitialState(): SimulationState {
  return {
    status: 'idle',
    runStarted: null,
    world: null,
    eventsByBranch: { A: [], B: [] },
    metricsByBranch: { A: [], B: [] },
    forks: [],
    scores: { A: null, B: null },
    credibility: null,
    recommendation: null,
    error: null,
    eventCount: 0,
  };
}

// ─── Reducer ──────────────────────────────────────────────────────────────────

type Action =
  | { type: 'CONNECTING' }
  | { type: 'STREAMING' }
  | { type: 'SSE_EVENT'; eventType: SSEEventType; data: unknown }
  | { type: 'ERROR'; message: string }
  | { type: 'RESET' };

function reducer(state: SimulationState, action: Action): SimulationState {
  switch (action.type) {
    case 'CONNECTING':
      return { ...makeInitialState(), status: 'connecting' };

    case 'STREAMING':
      return { ...state, status: 'streaming' };

    case 'RESET':
      return makeInitialState();

    case 'ERROR':
      return { ...state, status: 'error', error: action.message };

    case 'SSE_EVENT': {
      const next: SimulationState = { ...state, eventCount: state.eventCount + 1 };

      switch (action.eventType) {
        case 'run_started':
          return { ...next, status: 'streaming', runStarted: action.data as SimulationState['runStarted'] };

        case 'world_ready':
          return { ...next, world: action.data as SimulationState['world'] };

        case 'timeline_event': {
          const ev = action.data as TimelineEventPayload;
          const branch = ev.branch as Branch;
          return {
            ...next,
            eventsByBranch: {
              ...next.eventsByBranch,
              [branch]: [...next.eventsByBranch[branch], ev],
            },
          };
        }

        case 'metric': {
          const m = action.data as MetricPayload;
          const branch = m.branch as Branch;
          return {
            ...next,
            metricsByBranch: {
              ...next.metricsByBranch,
              [branch]: [...next.metricsByBranch[branch], m],
            },
          };
        }

        case 'fork_point':
          return {
            ...next,
            forks: [...next.forks, action.data as SimulationState['forks'][number]],
          };

        case 'branch_score': {
          const score = action.data as NonNullable<SimulationState['scores']['A']>;
          const branch = score.branch as Branch;
          return {
            ...next,
            scores: { ...next.scores, [branch]: score },
          };
        }

        case 'credibility':
          return { ...next, credibility: action.data as SimulationState['credibility'] };

        case 'recommendation':
          return { ...next, recommendation: action.data as SimulationState['recommendation'] };

        case 'error': {
          const errPayload = action.data as { message: string; recoverable: boolean };
          return { ...next, status: 'error', error: errPayload.message };
        }

        case 'done':
          return { ...next, status: 'done' };

        default:
          return next;
      }
    }
  }
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export interface UseSimulationReturn {
  state: SimulationState;
  /** Call with a SimulateRequest to start streaming. Pass useMock=true for local dev. */
  start: (req: SimulateRequest, useMock?: boolean) => void;
  /** Abort any in-flight stream and reset state. */
  reset: () => void;
}

export function useSimulation(): UseSimulationReturn {
  const [state, dispatch] = useReducer(reducer, makeInitialState());
  const abortRef = useRef<AbortController | null>(null);
  const mockCleanupRef = useRef<(() => void) | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    mockCleanupRef.current?.();
    dispatch({ type: 'RESET' });
  }, []);

  const start = useCallback((req: SimulateRequest, useMock = false) => {
    // Abort any previous stream
    abortRef.current?.abort();
    mockCleanupRef.current?.();

    dispatch({ type: 'CONNECTING' });

    if (useMock) {
      // ── Mock path (used with ?mock=1) ──────────────────────────────────────
      const cleanup = createMockStream(req, (eventType, data) => {
        dispatch({ type: 'SSE_EVENT', eventType: eventType as SSEEventType, data });
      });
      mockCleanupRef.current = cleanup;
      return;
    }

    // ── Real SSE path ─────────────────────────────────────────────────────────
    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      try {
        const res = await fetch('/api/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          const text = await res.text().catch(() => 'Unknown error');
          dispatch({ type: 'ERROR', message: `HTTP ${res.status}: ${text}` });
          return;
        }

        dispatch({ type: 'STREAMING' });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // SSE parsing: accumulate lines, fire on blank line
        let currentEventType: string | null = null;
        let currentData: string | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? ''; // keep last partial line in buffer

          for (const raw of lines) {
            const line = raw.trimEnd();

            if (line.startsWith('event:')) {
              currentEventType = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              currentData = line.slice(5).trim();
            } else if (line === '') {
              // Blank line → dispatch event
              if (currentEventType && currentData) {
                try {
                  const parsed = JSON.parse(currentData);
                  dispatch({ type: 'SSE_EVENT', eventType: currentEventType as SSEEventType, data: parsed });
                } catch {
                  // malformed JSON; skip
                }
              }
              currentEventType = null;
              currentData = null;
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return; // intentional abort
        const msg = err instanceof Error ? err.message : String(err);
        dispatch({ type: 'ERROR', message: msg });
      }
    })();
  }, []);

  return { state, start, reset };
}
