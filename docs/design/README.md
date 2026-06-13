# Lynsea — Frontend Design (Stitch)

The frontend visual design is authored in **Google Stitch** and mirrored here as the
source of truth for the implemented Next.js app (`frontend/`). The implementation must
match these design tokens and screen layouts. This file is the bridge between the
Stitch design and the code.

## Stitch project

- **Project:** `Lynsea — Decision Outcome Simulator` (`projects/8856869059858897506`)
- **Design system:** `Lynsea — Parallel Futures` (`assets/814583867362666778`)
- **Generator:** Gemini 3.1 Pro, desktop, dark mode.

## Design tokens (the contract for `frontend/`)

| Token | Value | Use |
|-------|-------|-----|
| canvas / background | `#0B0F1A` | app background (near-black navy) |
| surface (card) | `#141A29` | cards / panels |
| surface elevated | `#1B2336` | popovers, raised cards |
| border / outline | `#2A3346` | card borders; grid hairline `#1F2738` |
| text | `#E6EAF2` / secondary `#98A2B8` / muted `#5F6B82` | |
| **primary (brand)** | **`#8B7CF6`** (indigo) | neutral actions, focus ring, CTA |
| **Branch A** | **`#22D3EE`** (cyan) | Option A everywhere — timeline, curves, score, legend |
| **Branch B** | **`#FBBF24`** (amber) | Option B everywhere — timeline, curves, score, legend |
| **Branch C** (what-if) | **`#A78BFA`** (violet) | forked what-if branch overlay |
| fork point | `#F472B6` (magenta) | divergence marker + pulsing node |
| shared / perturbation | `#94A3B8` slate + **dashed** border | "same in both branches" controlled-variable events |
| positive / negative delta | `#34D399` / `#FB7185` | metric deltas |

- **Headline font:** Space Grotesk · **Body/label font:** Inter
- **Roundness:** 8px cards, 12px large panels, pill chips/badges
- **HARD RULE:** Branch A is **always cyan**, Branch B is **always amber** — never swap. Always pair color with the A/B label and left/right position (color-blind safe).
- **Copy tone:** PROBABILISTIC only ("likely", "~60% chance"), never "will/definitely" (`SYS-15`).

## Screens

Generated HTML + PNG live in `docs/design/stitch/`:

### 1. Decision Console — `stitch/decision-console.{html,png}`
The input / landing screen. One large decision input, a Quick/Medium/Heavy mode control,
and a collapsible "Refine your world" panel (profile + social circle), with the indigo
**Run simulation** CTA. → drives `POST /api/simulate`.

### 2. Parallel Futures Dashboard — `stitch/parallel-futures-dashboard.{html,png}`
The core result screen. Maps 1:1 to the SSE contract (`docs/api-contract.md`):

| Contract event | Dashboard region |
|----------------|------------------|
| `run_started` | header creates the two A/B columns + legend |
| `world_ready` | persona chips on event cards; option labels |
| `timeline_event` (skeleton) | solid branch-colored cards in each column |
| `timeline_event` (perturbation) | dashed slate "shared" cards at the same month in both columns |
| `metric` | the 5 dimensional-trajectory line charts (A vs B) |
| `fork_point` | magenta divergence marker + explanation |
| `branch_score` | the two composite score cards (value-weighted) |
| `credibility` | the circular credibility gauge + 3 sub-bars |
| `recommendation` | bottom strip — probabilistic leaning + guardrail |
| `error` | inline calm error card (never a white screen, `FE-29`) |
| `whatif` (P1) | "Ask a what-if…" input → branch C (violet) overlay |
| live "streaming…" pill | reflects events arriving in realtime over the SSE stream |

## Implementation note

`frontend/` (Next.js + Recharts) is built against `docs/api-contract.md`. After the
functional build lands, reconcile its styling to these tokens and to the two screen
layouts above (use the generated HTML in `stitch/` as the structural reference). The
Stitch HTML is Tailwind-based and can be lifted directly into components.
