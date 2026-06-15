'use client';

export interface UncertaintyTagProps {
  /** Optional custom label; defaults to bilingual "信息有限 / limited info" */
  label?: string;
  /** Size variant */
  size?: 'sm' | 'xs';
}

export default function UncertaintyTag({ label, size = 'xs' }: UncertaintyTagProps) {
  const text = label ?? '信息有限 / limited info';

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded-full border font-mono
        ${size === 'xs' ? 'text-[9px] px-1.5 py-0.5' : 'text-[11px] px-2 py-0.5'}
      `}
      style={{
        color: '#98A2B8',
        borderColor: '#2A3346',
        backgroundColor: '#1B2336',
      }}
      title="Low-confidence result — insufficient data or high causal uncertainty"
    >
      <span style={{ color: '#FBBF24' }}>~</span>
      {text}
    </span>
  );
}
