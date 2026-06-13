'use client';

/**
 * app/dashboard/page.tsx — Parallel Futures Dashboard (minimal shell)
 *
 * Owned by: FE-Console
 *
 * Responsibility:
 * - Reads the SimulateRequest from sessionStorage (set by the Console page)
 * - Starts the SSE stream (real or mock via ?mock=1)
 * - Renders two A/B columns (Branch A = cyan/left, Branch B = amber/right — NEVER swap)
 * - Shows a live "streaming…" pill
 * - Provides clearly-marked <TODO/> mount points for:
 *     • components/timeline  (FE-Dashboard)
 *     • components/charts    (FE-Dashboard)
 *     • components/forks     (FE-Insight)
 *     • components/credibility (FE-Insight)
 *     • components/recommendation (FE-Insight)
 *     • components/evidence  (FE-Insight)
 *
 * DO NOT implement those components here — leave the mount points only.
 */

import { useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useSimulation } from '@/lib/useSimulation';
import type { SimulateRequest, TimelineEventPayload } from '@/lib/contract';
import { Suspense } from 'react';

// ─── Branch color constants — HARD RULE: A=cyan, B=amber, never swap ─────────
const BRANCH_A_COLOR = '#22D3EE'; // cyan
const BRANCH_B_COLOR = '#FBBF24'; // amber

// ─── Streaming pill ──────────────────────────────────────────────────────────
function StreamingPill({ count, status }: { count: number; status: string }) {
  if (status === 'idle' || status === 'connecting') {
    return (
      <span className="px-3 py-1 rounded-full bg-[#181f31] border border-[#40475e]/30 font-label text-xs text-[#98A2B8] flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-[#6d758e]" />
        Connecting…
      </span>
    );
  }
  if (status === 'streaming') {
    return (
      <span className="px-3 py-1 rounded-full bg-[#181f31] border border-[#8B7CF6]/30 font-label text-xs text-[#8B7CF6] flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-[#8B7CF6] pulse-dot" />
        Streaming… {count} events
      </span>
    );
  }
  if (status === 'done') {
    return (
      <span className="px-3 py-1 rounded-full bg-[#065f46]/30 border border-[#34D399]/30 font-label text-xs text-[#34D399] flex items-center gap-2">
        ✓ Complete — {count} events
      </span>
    );
  }
  if (status === 'error') {
    return (
      <span className="px-3 py-1 rounded-full bg-[#8a1632]/30 border border-[#fb7185]/30 font-label text-xs text-[#fb7185] flex items-center gap-2">
        ⚠ Error
      </span>
    );
  }
  return null;
}

// ─── Inline event card (placeholder until FE-Dashboard lands timeline component) ──
function EventCard({ event, branch }: { event: TimelineEventPayload; branch: 'A' | 'B' }) {
  const color = branch === 'A' ? BRANCH_A_COLOR : BRANCH_B_COLOR;
  const isShared = event.kind === 'perturbation';

  return (
    <div
      className={`rounded-lg p-3 mb-3 relative ${
        isShared
          ? 'bg-[#131929] shared-event-card'
          : 'bg-[#131929]'
      }`}
      style={isShared ? undefined : { borderLeft: `2px solid ${color}` }}
    >
      {isShared && (
        <div className="absolute -top-2 left-3 bg-[#1d253a] px-1.5 py-0.5 rounded font-caption text-[10px] text-[#98A2B8] uppercase tracking-wide flex items-center gap-1">
          ≡ Shared Event
        </div>
      )}
      <p className="font-title text-sm text-[#E6EAF2] mb-1 mt-1">{event.title}</p>
      <p className="font-caption text-[11px] text-[#98A2B8] leading-relaxed">{event.detail}</p>
      <div className="flex gap-1 mt-2">
        <span className="font-caption text-[10px] text-[#5F6B82]">M{event.month}</span>
        {event.personas.slice(0, 3).map(p => (
          <span key={p} className="px-1.5 py-0.5 rounded bg-[#1d253a] font-caption text-[10px] text-[#98A2B8]">{p}</span>
        ))}
      </div>
    </div>
  );
}

// ─── Error card ──────────────────────────────────────────────────────────────
function ErrorCard({ message }: { message: string }) {
  return (
    <div className="mx-auto max-w-lg mt-12 bg-[#8a1632]/20 border border-[#fb7185]/30 rounded-lg p-6">
      <p className="font-title text-base text-[#fb7185] mb-2">Simulation error</p>
      <p className="font-body text-sm text-[#98A2B8]">{message}</p>
      <p className="font-caption text-[11px] text-[#6d758e] mt-3">
        Try returning to the Console and re-running. This may be a transient error.
      </p>
    </div>
  );
}

// ─── Main dashboard content ──────────────────────────────────────────────────
function DashboardContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { state, start, reset } = useSimulation();
  const startedRef = useRef(false);

  const useMock = searchParams.get('mock') === '1';

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    // Load the SimulateRequest from session storage (set by Console page)
    let req: SimulateRequest | null = null;
    try {
      const raw = sessionStorage.getItem('lynsea_request');
      if (raw) req = JSON.parse(raw) as SimulateRequest;
    } catch {
      // ignore parse errors
    }

    // If no request stored and not mock mode, fall back to a sensible default for ?mock=1
    if (!req) {
      req = {
        decision: 'Should I quit my stable job to join an early-stage startup?',
        mode: 'quick',
        options: ['Stay at current job', 'Join the startup'],
      };
    }

    start(req, useMock);

    return () => {
      reset();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { status, runStarted, world, eventsByBranch, scores, credibility, recommendation, error, eventCount, forks } = state;

  const optionA = world?.options?.A ?? 'Option A';
  const optionB = world?.options?.B ?? 'Option B';

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Navigation ── */}
      <nav className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-6 h-16 bg-[#0a0e19]/90 backdrop-blur-md border-b border-[#1d253a]">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/')}
            className="font-display font-bold text-[#8B7CF6] text-xl tracking-tight hover:opacity-80 transition-opacity"
          >
            ⊙ Lynsea
          </button>
          <nav className="hidden md:flex gap-4 ml-8">
            <a href="/" className="font-body text-sm text-[#98A2B8] hover:text-[#E6EAF2] transition-colors">Console</a>
            <span className="font-body text-sm text-[#8B7CF6] border-b border-[#8B7CF6] pb-0.5">Observatory</span>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <StreamingPill count={eventCount} status={status} />
          {status === 'done' && (
            <button
              onClick={() => router.push('/')}
              className="px-3 py-1.5 bg-[#8B7CF6]/20 border border-[#8B7CF6]/30 rounded-lg font-label text-xs text-[#8B7CF6] hover:bg-[#8B7CF6]/30 transition-colors"
            >
              New simulation
            </button>
          )}
        </div>
      </nav>

      {/* ── Dashboard header (decision + legend) ── */}
      <div className="pt-20 px-6 pb-4 border-b border-[#1d253a]/50 bg-[#0B0F1A]/90 backdrop-blur-sm sticky top-16 z-20">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
          <div className="max-w-2xl">
            <p className="font-caption text-[11px] text-[#98A2B8] uppercase tracking-wider mb-1">Decision Matrix</p>
            <h1 className="font-headline text-[22px] leading-7 font-semibold text-[#E6EAF2]">
              {runStarted
                ? sessionStorage.getItem('lynsea_request')
                  ? JSON.parse(sessionStorage.getItem('lynsea_request')!).decision
                  : 'Simulation in progress…'
                : 'Preparing simulation…'}
            </h1>
          </div>
          {/* Branch legend — HARD RULE: A = cyan, B = amber, always */}
          <div className="flex gap-3">
            <div className="flex items-center gap-2 bg-[#131929] px-3 py-1.5 rounded-full border border-[#2A3346]">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: BRANCH_A_COLOR, boxShadow: '0 0 8px rgba(34,211,238,0.4)' }} />
              <span className="font-label text-xs text-[#E6EAF2]">A — {optionA}</span>
            </div>
            <div className="flex items-center gap-2 bg-[#131929] px-3 py-1.5 rounded-full border border-[#2A3346]">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: BRANCH_B_COLOR, boxShadow: '0 0 8px rgba(251,191,36,0.4)' }} />
              <span className="font-label text-xs text-[#E6EAF2]">B — {optionB}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Main content area ── */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6">

        {/* Error state */}
        {status === 'error' && error && <ErrorCard message={error} />}

        {/* ── Two-column layout: Branch A (cyan/left) | Branch B (amber/right) ── */}
        {status !== 'error' && (
          <div className="flex gap-4">
            {/* ── Branch A column — ALWAYS cyan, ALWAYS left ── */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-4 sticky top-[136px] z-10 bg-[#0B0F1A] py-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: BRANCH_A_COLOR }} />
                <h2 className="font-title text-sm font-semibold" style={{ color: BRANCH_A_COLOR }}>
                  Branch A
                </h2>
                <span className="font-caption text-[11px] text-[#98A2B8] truncate">{optionA}</span>
              </div>

              {/* ── TODO: mount point for components/timeline (FE-Dashboard) ── */}
              {/* <TimelineColumn branch="A" events={eventsByBranch.A} /> */}

              {/* Interim inline event cards until FE-Dashboard lands */}
              <div>
                {eventsByBranch.A.length === 0 && (status === 'connecting' || status === 'streaming') && (
                  <div className="bg-[#131929] border border-[#2A3346] rounded-lg p-4 mb-3 animate-pulse">
                    <div className="h-3 bg-[#1d253a] rounded w-3/4 mb-2" />
                    <div className="h-2 bg-[#1d253a] rounded w-full mb-1" />
                    <div className="h-2 bg-[#1d253a] rounded w-2/3" />
                  </div>
                )}
                {eventsByBranch.A.map(ev => (
                  <EventCard key={ev.event_id} event={ev} branch="A" />
                ))}
              </div>

              {/* Branch A score card */}
              {scores.A && (
                <div className="mt-4 bg-[#131929] border border-[#2A3346] rounded-lg p-4" style={{ borderLeftColor: BRANCH_A_COLOR, borderLeftWidth: 2 }}>
                  <p className="font-caption text-[11px] text-[#98A2B8] uppercase tracking-wider mb-2">Branch A Score (value-weighted)</p>
                  <div className="font-display text-[32px] font-bold" style={{ color: BRANCH_A_COLOR }}>
                    {scores.A.total}
                  </div>
                  <div className="mt-2 space-y-1">
                    {Object.entries(scores.A.breakdown).map(([dim, val]) => (
                      <div key={dim} className="flex justify-between font-caption text-[11px]">
                        <span className="text-[#98A2B8]">{dim.replace('_', ' ')}</span>
                        <span className="text-[#E6EAF2]">{val}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* ── Central axis divider ── */}
            <div className="w-px bg-[#2A3346] hidden md:block" />

            {/* ── Branch B column — ALWAYS amber, ALWAYS right ── */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-4 sticky top-[136px] z-10 bg-[#0B0F1A] py-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: BRANCH_B_COLOR }} />
                <h2 className="font-title text-sm font-semibold" style={{ color: BRANCH_B_COLOR }}>
                  Branch B
                </h2>
                <span className="font-caption text-[11px] text-[#98A2B8] truncate">{optionB}</span>
              </div>

              {/* ── TODO: mount point for components/timeline (FE-Dashboard) ── */}
              {/* <TimelineColumn branch="B" events={eventsByBranch.B} /> */}

              {/* Interim inline event cards until FE-Dashboard lands */}
              <div>
                {eventsByBranch.B.length === 0 && (status === 'connecting' || status === 'streaming') && (
                  <div className="bg-[#131929] border border-[#2A3346] rounded-lg p-4 mb-3 animate-pulse">
                    <div className="h-3 bg-[#1d253a] rounded w-3/4 mb-2" />
                    <div className="h-2 bg-[#1d253a] rounded w-full mb-1" />
                    <div className="h-2 bg-[#1d253a] rounded w-2/3" />
                  </div>
                )}
                {eventsByBranch.B.map(ev => (
                  <EventCard key={ev.event_id} event={ev} branch="B" />
                ))}
              </div>

              {/* Branch B score card */}
              {scores.B && (
                <div className="mt-4 bg-[#131929] border border-[#2A3346] rounded-lg p-4" style={{ borderLeftColor: BRANCH_B_COLOR, borderLeftWidth: 2 }}>
                  <p className="font-caption text-[11px] text-[#98A2B8] uppercase tracking-wider mb-2">Branch B Score (value-weighted)</p>
                  <div className="font-display text-[32px] font-bold" style={{ color: BRANCH_B_COLOR }}>
                    {scores.B.total}
                  </div>
                  <div className="mt-2 space-y-1">
                    {Object.entries(scores.B.breakdown).map(([dim, val]) => (
                      <div key={dim} className="flex justify-between font-caption text-[11px]">
                        <span className="text-[#98A2B8]">{dim.replace('_', ' ')}</span>
                        <span className="text-[#E6EAF2]">{val}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── TODO: mount point for components/charts (FE-Dashboard) ── */}
        {/* <DimensionalCharts metricsByBranch={state.metricsByBranch} /> */}

        {/* ── TODO: mount point for components/forks (FE-Insight) ── */}
        {/* <ForkPoints forks={state.forks} /> */}
        {forks.length > 0 && (
          <div className="mt-6">
            <p className="font-caption text-[11px] text-[#F472B6] uppercase tracking-wider mb-2">Fork Points</p>
            {forks.map((fork, i) => (
              <div key={i} className="bg-[#131929] border border-[#F472B6]/30 rounded-lg p-4 mb-3" style={{ boxShadow: '0 0 12px rgba(244,114,182,0.15)' }}>
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-3 h-3 rounded-full bg-[#F472B6] animate-pulse" />
                  <span className="font-title text-sm text-[#F472B6]">M{fork.month} — {fork.title}</span>
                  <span className="ml-auto font-data-numeric text-xs text-[#98A2B8]">magnitude {fork.magnitude}/100</span>
                </div>
                <p className="font-caption text-[11px] text-[#98A2B8]">{fork.explanation}</p>
              </div>
            ))}
          </div>
        )}

        {/* ── TODO: mount point for components/credibility (FE-Insight) ── */}
        {/* <CredibilityCard credibility={state.credibility} /> */}
        {credibility && (
          <div className="mt-6 bg-[#131929] border border-[#2A3346] rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="font-label text-sm text-[#E6EAF2]">Simulation Credibility</p>
              <span className="font-data-numeric text-sm text-[#E6EAF2]">{credibility.overall}/100</span>
            </div>
            {Object.entries(credibility.breakdown).map(([key, val]) => (
              <div key={key} className="mb-2">
                <div className="flex justify-between font-caption text-[11px] text-[#98A2B8] mb-1">
                  <span>{key.replace(/_/g, ' ')}</span>
                  <span>{val}</span>
                </div>
                <div className="h-1 bg-[#1d253a] rounded-full overflow-hidden">
                  <div className="h-full bg-[#6d758e] rounded-full" style={{ width: `${val}%` }} />
                </div>
              </div>
            ))}
            <p className="font-caption text-[10px] text-[#5F6B82] italic mt-2">{credibility.notes}</p>
          </div>
        )}

        {/* ── TODO: mount point for components/recommendation (FE-Insight) ── */}
        {/* <RecommendationStrip recommendation={state.recommendation} /> */}

        {/* ── TODO: mount point for components/evidence (FE-Insight) ── */}
        {/* <EvidenceDrilldown /> */}
      </main>

      {/* ── Bottom recommendation strip ── */}
      {recommendation && (
        <div className="sticky bottom-0 bg-[#141A29] border-t border-[#2A3346] p-4 z-30">
          <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="font-label text-sm font-bold text-[#E6EAF2]"
                  style={{ color: recommendation.leaning === 'A' ? BRANCH_A_COLOR : recommendation.leaning === 'B' ? BRANCH_B_COLOR : '#8B7CF6' }}
                >
                  {recommendation.leaning === 'neither'
                    ? 'No strong leaning — roughly equal probability either path serves you well.'
                    : `Leans Branch ${recommendation.leaning}`}
                </span>
              </div>
              <p className="font-caption text-[11px] text-[#98A2B8] max-w-xl">{recommendation.rationale}</p>
              {recommendation.guardrail && (
                <p className="font-caption text-[10px] text-[#6d758e] mt-1 uppercase tracking-wide">
                  ⚠ {recommendation.guardrail}
                </p>
              )}
              <p className="font-caption text-[10px] text-[#5F6B82] mt-1">
                This is a probabilistic simulation, not a deterministic prediction — change any assumption and re-run.
              </p>
            </div>
            <button
              onClick={() => router.push('/')}
              className="flex-shrink-0 px-4 py-2 bg-[#8B7CF6]/10 border border-[#8B7CF6]/30 rounded-lg text-[#8B7CF6] font-label text-sm hover:bg-[#8B7CF6]/20 transition-colors flex items-center gap-2"
            >
              + New simulation
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Page wrapper with Suspense (required for useSearchParams) ────────────────
export default function DashboardPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-[#98A2B8] font-body text-sm">Loading simulation…</p>
      </div>
    }>
      <DashboardContent />
    </Suspense>
  );
}
