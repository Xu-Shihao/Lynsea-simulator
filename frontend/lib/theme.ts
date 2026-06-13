import type { Branch, Stance } from "./types";

// Branch color coding used consistently across personas, timelines, charts.
// Stitch palette: Branch A = brand-cyan, Branch B = brand-amber.
export const BRANCH_COLORS: Record<Branch, string> = {
  A: "#22D3EE", // brand-cyan
  B: "#FBBF24", // brand-amber
};

// Soft / translucent backgrounds for branch surfaces.
export const BRANCH_SOFT: Record<Branch, string> = {
  A: "rgba(34, 211, 238, 0.12)",
  B: "rgba(251, 191, 36, 0.12)",
};

// Glow box-shadow per branch (matches the .glow-cyan / .glow-amber classes).
export const BRANCH_GLOW: Record<Branch, string> = {
  A: "0 0 15px rgba(34, 211, 238, 0.2)",
  B: "0 0 15px rgba(251, 191, 36, 0.2)",
};

// Shared exogenous events: neutral slate (rendered with a dashed border).
export const SHARED_COLOR = "#a3aac5"; // on-surface-variant (neutral slate)

// what-if / Branch C accent.
export const MAGENTA = "#F472B6"; // brand-magenta

export function branchColor(b: Branch): string {
  return BRANCH_COLORS[b];
}

// Stance pills, dark-theme friendly.
export const STANCE_STYLES: Record<
  Stance,
  { label: string; bg: string; fg: string; border: string }
> = {
  supportive: {
    label: "Supportive",
    bg: "rgba(52, 211, 153, 0.12)",
    fg: "#34d399",
    border: "rgba(52, 211, 153, 0.4)",
  },
  opposed: {
    label: "Opposed",
    bg: "rgba(200, 71, 93, 0.15)",
    fg: "#fd6f85",
    border: "rgba(200, 71, 93, 0.45)",
  },
  neutral: {
    label: "Neutral",
    bg: "rgba(109, 117, 142, 0.18)",
    fg: "#a3aac5",
    border: "rgba(109, 117, 142, 0.45)",
  },
  unknown: {
    label: "Unknown",
    bg: "rgba(64, 71, 94, 0.3)",
    fg: "#a3aac5",
    border: "rgba(64, 71, 94, 0.6)",
  },
};

// Map a 0..1 credibility score to a qualitative band + color.
export function credibilityBand(score: number): {
  label: string;
  color: string;
} {
  if (score >= 0.7) return { label: "Reasonably grounded", color: "#34d399" };
  if (score >= 0.45) return { label: "Directional", color: "#fbbf24" };
  return { label: "Speculative", color: "#fd6f85" };
}
