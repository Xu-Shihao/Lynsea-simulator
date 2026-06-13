'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { SimulateRequest, SimulationMode, SocialCircleMember } from '@/lib/contract';

// ─── Mode selector ───────────────────────────────────────────────────────────
const MODES: { value: SimulationMode; label: string; desc: string }[] = [
  { value: 'quick', label: 'Quick (≤10 min)', desc: '6 months, 2 branches, 3–5 personas' },
  { value: 'medium', label: 'Medium (≤1 hr)', desc: '12–24 months, deeper narrative' },
  { value: 'heavy', label: 'Heavy', desc: '24+ months, full distribution analysis' },
];

// ─── Social stance options ────────────────────────────────────────────────────
const STANCES = ['supportive', 'neutral', 'opposed'] as const;

// ─── Default social circle members ───────────────────────────────────────────
const defaultCircle: SocialCircleMember[] = [
  { role: 'partner', influence_weight: 8, stance_on_decision: 'opposed', key_concerns: ['stability', 'income'] },
  { role: 'mother', influence_weight: 6, stance_on_decision: 'opposed' },
];

export default function DecisionConsolePage() {
  const router = useRouter();

  // Form state
  const [decision, setDecision] = useState('');
  const [mode, setMode] = useState<SimulationMode>('quick');
  const [showRefine, setShowRefine] = useState(false);

  // Profile
  const [age, setAge] = useState<number | ''>('');
  const [city, setCity] = useState('');
  const [occupation, setOccupation] = useState('');
  const [riskTolerance, setRiskTolerance] = useState(5);
  const [coreValues, setCoreValues] = useState<string[]>([]);
  const [valueInput, setValueInput] = useState('');
  const [decisionStyle, setDecisionStyle] = useState('');

  // Social circle
  const [socialCircle, setSocialCircle] = useState<SocialCircleMember[]>(defaultCircle);

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [charCount, setCharCount] = useState(0);

  // ─── Handlers ───────────────────────────────────────────────────────────────

  function handleDecisionChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setDecision(e.target.value);
    setCharCount(e.target.value.length);
  }

  function addCoreValue() {
    const v = valueInput.trim();
    if (v && !coreValues.includes(v)) {
      setCoreValues([...coreValues, v]);
    }
    setValueInput('');
  }

  function removeValue(v: string) {
    setCoreValues(coreValues.filter(x => x !== v));
  }

  function addCircleMember() {
    setSocialCircle([...socialCircle, { role: '', influence_weight: 5, stance_on_decision: 'neutral' }]);
  }

  function updateMember(idx: number, patch: Partial<SocialCircleMember>) {
    setSocialCircle(prev => prev.map((m, i) => (i === idx ? { ...m, ...patch } : m)));
  }

  function removeMember(idx: number) {
    setSocialCircle(prev => prev.filter((_, i) => i !== idx));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!decision.trim()) return;

    setIsSubmitting(true);

    const body: SimulateRequest = {
      decision: decision.trim(),
      mode,
      ...(age !== '' && city && occupation
        ? {
            profile: {
              age: Number(age),
              city,
              occupation,
              risk_tolerance: riskTolerance,
              core_values: coreValues,
              decision_style: decisionStyle || undefined,
            },
          }
        : {}),
      ...(socialCircle.length > 0 ? { social_circle: socialCircle.filter(m => m.role) } : {}),
    };

    // Store form payload in sessionStorage so the dashboard can pick it up
    sessionStorage.setItem('lynsea_request', JSON.stringify(body));

    // Navigate to dashboard; the SSE hook will start there
    router.push('/dashboard');
  }

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Top navigation ── */}
      <nav className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-6 h-16 bg-[#0a0e19] border-b border-[#1d253a]">
        <div className="flex items-center gap-4">
          <div className="font-display font-bold text-[#8B7CF6] text-xl tracking-tight">
            ⊙ Lynsea
          </div>
          <div className="hidden md:flex items-center gap-6 ml-10">
            <a href="/" className="font-body text-sm text-[#8B7CF6] border-b-2 border-[#8B7CF6] pb-1 font-medium">
              Console
            </a>
            <a href="#" className="font-body text-sm text-[#98A2B8] hover:text-[#E6EAF2] transition-colors">
              Archive
            </a>
            <a href="#" className="font-body text-sm text-[#98A2B8] hover:text-[#E6EAF2] transition-colors">
              Observatory
            </a>
          </div>
        </div>
        <div className="flex items-center gap-3 text-[#8B7CF6]">
          <button className="opacity-80 hover:opacity-100 transition-opacity" aria-label="Settings">⚙</button>
          <button className="opacity-80 hover:opacity-100 transition-opacity" aria-label="Account">◎</button>
        </div>
      </nav>

      {/* ── Main content ── */}
      <main className="flex-grow flex flex-col items-center justify-center pt-32 pb-24 px-6 w-full max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="font-display text-[40px] leading-[48px] font-bold text-[#E6EAF2] mb-2 tracking-tight">
            See your futures before you choose.
          </h1>
          <p className="font-body text-base text-[#98A2B8] max-w-2xl mx-auto">
            Describe a complex life decision. Lynsea will simulate probabilistic parallel futures,
            mapping out likely consequences to help you navigate uncertainty with clarity.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="w-full space-y-4">
          {/* Decision input card */}
          <div className="w-full bg-[#131929] rounded-xl border border-[#2A3346] glow-border transition-all duration-300 relative overflow-hidden shadow-2xl">
            {/* Indigo accent left border */}
            <div className="absolute top-0 left-0 w-1 h-full bg-[#8B7CF6]" />

            <textarea
              className="w-full h-40 bg-transparent border-none text-[#E6EAF2] font-body text-base pl-6 pr-6 pt-5 pb-3 resize-none focus:ring-0 focus:outline-none placeholder-[#5F6B82]"
              placeholder="What are you deciding? What do you want to predict? Who or what will be affected?"
              value={decision}
              onChange={handleDecisionChange}
              maxLength={2000}
              required
            />

            {/* Mode selector row */}
            <div className="flex flex-wrap items-center justify-between px-6 py-4 border-t border-[#2A3346] bg-[#0e1320] gap-3">
              <div className="flex items-center gap-3">
                <span className="font-label text-xs text-[#98A2B8] uppercase tracking-wider">Mode</span>
                <div className="flex bg-[#181f31] rounded-full p-1 border border-[#40475e]/30">
                  {MODES.map(m => (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => setMode(m.value)}
                      className={`px-4 py-1.5 rounded-full font-label text-xs transition-all ${
                        mode === m.value
                          ? 'bg-[#8B7CF6]/20 text-[#8B7CF6] border border-[#8B7CF6]/30'
                          : 'text-[#98A2B8] hover:text-[#E6EAF2]'
                      }`}
                      title={m.desc}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-caption text-[11px] text-[#6d758e]">
                  {charCount > 0 ? `${charCount} chars` : 'Quick mode: 6 months, 2 branches, 3–5 personas'}
                </span>
              </div>
            </div>
          </div>

          {/* Collapsible "Refine your world" panel */}
          <div className="w-full bg-[#0e1320] rounded-lg border border-[#2A3346] overflow-hidden">
            <button
              type="button"
              onClick={() => setShowRefine(prev => !prev)}
              className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-[#131929] transition-colors border-b border-[#2A3346]"
            >
              <div className="flex items-center gap-2">
                <span className="text-[#8B7CF6]">⊟</span>
                <span className="font-title text-base text-[#E6EAF2]">Refine your world</span>
                <span className="font-caption text-[11px] text-[#6d758e] ml-1">(optional — better predictions with more context)</span>
              </div>
              <span className="text-[#98A2B8] text-lg">{showRefine ? '▲' : '▼'}</span>
            </button>

            {showRefine && (
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-10">
                {/* Subject profile */}
                <div className="space-y-4">
                  <h3 className="font-label text-xs text-[#6d758e] uppercase tracking-wider mb-2">Subject Profile</h3>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-[#131929] p-2 rounded border border-[#2A3346]">
                      <label className="block font-caption text-[11px] text-[#6d758e] mb-1">Age</label>
                      <input
                        type="number"
                        min={16} max={100}
                        value={age}
                        onChange={e => setAge(e.target.value === '' ? '' : Number(e.target.value))}
                        placeholder="—"
                        className="w-full bg-transparent text-[#E6EAF2] font-data-numeric text-sm focus:outline-none"
                      />
                    </div>
                    <div className="bg-[#131929] p-2 rounded border border-[#2A3346]">
                      <label className="block font-caption text-[11px] text-[#6d758e] mb-1">City</label>
                      <input
                        type="text"
                        value={city}
                        onChange={e => setCity(e.target.value)}
                        placeholder="—"
                        className="w-full bg-transparent text-[#E6EAF2] font-body text-sm focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="bg-[#131929] p-2 rounded border border-[#2A3346]">
                    <label className="block font-caption text-[11px] text-[#6d758e] mb-1">Occupation</label>
                    <input
                      type="text"
                      value={occupation}
                      onChange={e => setOccupation(e.target.value)}
                      placeholder="—"
                      className="w-full bg-transparent text-[#E6EAF2] font-body text-sm focus:outline-none"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="font-caption text-[11px] text-[#6d758e]">Risk Tolerance</span>
                      <span className="font-data-numeric text-xs text-[#8B7CF6]">{riskTolerance}/10</span>
                    </div>
                    <input
                      type="range"
                      min={1} max={10}
                      value={riskTolerance}
                      onChange={e => setRiskTolerance(Number(e.target.value))}
                      className="w-full accent-[#8B7CF6]"
                    />
                  </div>

                  <div>
                    <span className="block font-caption text-[11px] text-[#6d758e] mb-2">Core Values</span>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {coreValues.map(v => (
                        <span
                          key={v}
                          className="flex items-center gap-1 px-3 py-1 rounded-full bg-[#131929] border border-[#40475e] text-[#E6EAF2] font-label text-xs"
                        >
                          {v}
                          <button type="button" onClick={() => removeValue(v)} className="text-[#98A2B8] hover:text-[#E6EAF2] ml-1">×</button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={valueInput}
                        onChange={e => setValueInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCoreValue(); } }}
                        placeholder="Add a value (e.g. growth)"
                        className="flex-1 bg-[#131929] border border-[#2A3346] rounded px-2 py-1 text-[#E6EAF2] font-body text-xs focus:outline-none focus:border-[#8B7CF6]"
                      />
                      <button
                        type="button"
                        onClick={addCoreValue}
                        className="px-3 py-1 bg-[#8B7CF6]/20 border border-[#8B7CF6]/30 rounded text-[#8B7CF6] font-label text-xs hover:bg-[#8B7CF6]/30 transition-colors"
                      >
                        Add
                      </button>
                    </div>
                  </div>

                  <div className="bg-[#131929] p-2 rounded border border-[#2A3346]">
                    <label className="block font-caption text-[11px] text-[#6d758e] mb-1">Decision Style</label>
                    <select
                      value={decisionStyle}
                      onChange={e => setDecisionStyle(e.target.value)}
                      className="w-full bg-transparent text-[#E6EAF2] font-body text-sm focus:outline-none"
                    >
                      <option value="">— unspecified —</option>
                      <option value="analytical">Analytical</option>
                      <option value="intuitive">Intuitive</option>
                      <option value="collaborative">Collaborative</option>
                      <option value="directive">Directive</option>
                    </select>
                  </div>
                </div>

                {/* Social circle */}
                <div className="space-y-3">
                  <h3 className="font-label text-xs text-[#6d758e] uppercase tracking-wider mb-2">Social Circle Influences</h3>

                  {socialCircle.map((member, idx) => (
                    <div key={idx} className="flex items-start justify-between bg-[#131929] p-3 rounded border border-[#2A3346] gap-3">
                      <div className="flex-1 space-y-2">
                        <input
                          type="text"
                          value={member.role}
                          onChange={e => updateMember(idx, { role: e.target.value })}
                          placeholder="Role (e.g. partner, friend)"
                          className="w-full bg-transparent text-[#E6EAF2] font-body text-sm focus:outline-none border-b border-[#2A3346] pb-1"
                        />
                        <div className="flex items-center gap-3">
                          <span className="font-caption text-[11px] text-[#6d758e]">Influence</span>
                          <input
                            type="range"
                            min={1} max={10}
                            value={member.influence_weight}
                            onChange={e => updateMember(idx, { influence_weight: Number(e.target.value) })}
                            className="flex-1 accent-[#8B7CF6]"
                          />
                          <span className="font-data-numeric text-xs text-[#8B7CF6] w-4">{member.influence_weight}</span>
                        </div>
                        <div className="flex gap-1">
                          {STANCES.map(s => (
                            <button
                              key={s}
                              type="button"
                              onClick={() => updateMember(idx, { stance_on_decision: s })}
                              className={`px-2 py-0.5 rounded font-caption text-[10px] transition-colors ${
                                member.stance_on_decision === s
                                  ? s === 'opposed'
                                    ? 'bg-[#8a1632] text-[#fb7185]'
                                    : s === 'supportive'
                                    ? 'bg-[#065f46] text-[#34D399]'
                                    : 'bg-[#181f31] text-[#98A2B8]'
                                  : 'text-[#6d758e] hover:text-[#98A2B8]'
                              }`}
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeMember(idx)}
                        className="text-[#6d758e] hover:text-[#fb7185] transition-colors text-lg leading-none mt-1"
                        aria-label="Remove member"
                      >
                        ×
                      </button>
                    </div>
                  ))}

                  <button
                    type="button"
                    onClick={addCircleMember}
                    className="w-full py-2 border border-dashed border-[#40475e] rounded text-[#98A2B8] font-label text-xs hover:text-[#8B7CF6] hover:border-[#8B7CF6]/50 transition-colors flex justify-center items-center gap-1"
                  >
                    + Add Influence
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Run simulation CTA */}
          <div className="flex justify-center pt-2">
            <button
              type="submit"
              disabled={!decision.trim() || isSubmitting}
              className="bg-[#8B7CF6] hover:bg-[#9d8fff] disabled:opacity-40 disabled:cursor-not-allowed text-[#230086] font-title text-lg font-semibold py-4 px-10 rounded-lg glow-primary transition-all flex items-center gap-3 group"
            >
              {isSubmitting ? (
                <>
                  <span className="animate-spin">⟳</span>
                  Starting simulation…
                </>
              ) : (
                <>
                  Run simulation
                  <span className="group-hover:translate-x-1 transition-transform">→</span>
                </>
              )}
            </button>
          </div>
        </form>
      </main>

      {/* ── Footer ── */}
      <footer className="w-full py-4 px-6 flex flex-col md:flex-row justify-between items-center gap-2 bg-[#0a0e19] border-t border-[#1d253a] mt-auto">
        <div className="font-caption text-[11px] text-[#6d758e]">
          © 2024 Lynsea. Simulations are probabilistic models, not deterministic predictions.
        </div>
        <div className="flex gap-6">
          <a href="#" className="font-caption text-[11px] text-[#98A2B8] hover:text-[#ffd16f] transition-colors">Terms of Service</a>
          <a href="#" className="font-caption text-[11px] text-[#98A2B8] hover:text-[#ffd16f] transition-colors">Privacy Policy</a>
          <a href="#" className="font-caption text-[11px] text-[#98A2B8] hover:text-[#ffd16f] transition-colors">Methodology</a>
        </div>
      </footer>
    </div>
  );
}
