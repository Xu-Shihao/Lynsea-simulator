import type { Branch, Stance } from "./types";

// Branch color coding used consistently across personas, timelines, charts.
export const BRANCH_COLORS: Record<Branch, string> = {
  A: "#0d9488", // teal
  B: "#d97706", // amber
};

export const BRANCH_SOFT: Record<Branch, string> = {
  A: "#ccfbf1",
  B: "#fef3c7",
};

export const SHARED_COLOR = "#7c3aed"; // violet for shared exogenous events

export function branchColor(b: Branch): string {
  return BRANCH_COLORS[b];
}

export const STANCE_STYLES: Record<
  Stance,
  { label: string; bg: string; fg: string }
> = {
  supportive: { label: "Supportive", bg: "#dcfce7", fg: "#166534" },
  opposed: { label: "Opposed", bg: "#fee2e2", fg: "#991b1b" },
  neutral: { label: "Neutral", bg: "#e2e8f0", fg: "#334155" },
  unknown: { label: "Unknown", bg: "#f1f5f9", fg: "#64748b" },
};

// Map a 0..1 credibility score to a qualitative band + color.
export function credibilityBand(score: number): {
  label: string;
  color: string;
} {
  if (score >= 0.7) return { label: "Reasonably grounded", color: "#16a34a" };
  if (score >= 0.45) return { label: "Directional", color: "#d97706" };
  return { label: "Speculative", color: "#dc2626" };
}
