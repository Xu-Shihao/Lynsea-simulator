# FE-Insight Component Mounting Guide

Each component is a default export. Props are typed in `lib/contract.ts`.

| Component | Import path | Props |
|-----------|-------------|-------|
| `ForkPoints` | `@/components/forks/ForkPoints` | `{ forks: ForkPointPayload[] }` |
| `CredibilityCard` | `@/components/credibility/CredibilityCard` | `{ credibility: CredibilityPayload }` |
| `RecommendationStrip` | `@/components/recommendation/RecommendationStrip` | `{ recommendation: RecommendationPayload }` |
| `EvidencePopover` | `@/components/evidence/EvidencePopover` | `{ event: TimelineEventPayload; children: ReactNode; placement?: 'top' \| 'bottom' }` |
| `UncertaintyTag` | `@/components/common/UncertaintyTag` | `{ label?: string; size?: 'sm' \| 'xs' }` |

## Usage sketch

```tsx
import ForkPoints from '@/components/forks/ForkPoints';
import CredibilityCard from '@/components/credibility/CredibilityCard';
import RecommendationStrip from '@/components/recommendation/RecommendationStrip';
import EvidencePopover from '@/components/evidence/EvidencePopover';
import UncertaintyTag from '@/components/common/UncertaintyTag';

// Fork divergence section (after DimensionalCharts)
<ForkPoints forks={state.forks} />

// Credibility card (after fork points)
{state.credibility && <CredibilityCard credibility={state.credibility} />}

// Recommendation strip — sticky bottom bar
{state.recommendation && <RecommendationStrip recommendation={state.recommendation} />}

// Wrap any timeline event card to add evidence drill-down
<EvidencePopover event={event}>
  <YourEventCard event={event} />
</EvidencePopover>

// Low-confidence badge on persona chips or metric cards
<UncertaintyTag />                          // default bilingual label
<UncertaintyTag label="low confidence" />   // custom label
```

## Design tokens applied

- Background: `#0B0F1A` canvas · `#141A29` surface · `#1B2336` elevated  
- Fork accent: `#F472B6` magenta (pulsing node + diff band)  
- Branch A: `#22D3EE` cyan · Branch B: `#FBBF24` amber (NEVER swap)  
- Primary: `#8B7CF6` indigo  
- Text: `#E6EAF2` / `#98A2B8` secondary / `#5F6B82` muted  
