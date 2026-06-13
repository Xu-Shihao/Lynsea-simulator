"use client";

import { useState } from "react";
import { Icon } from "./Brand";

/**
 * "Ask a what-if… (Branch C)" entry. There is no backend support for a third
 * branch yet, so this is a stubbed affordance (magenta accent): it captures the
 * user's hypothetical and acknowledges it is queued, without fabricating a
 * simulated result. Keeps the UX honest while matching the Stitch design.
 */
export function WhatIfEntry() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="relative">
      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="bg-primary-container/10 border border-primary-container text-primary rounded-lg px-4 py-2 font-label text-label flex items-center gap-2 hover:bg-primary-container/20 transition-colors focus-ring"
        >
          <Icon name="add_circle" className="text-[18px]" />
          Ask a what-if…
          <span className="bg-brand-magenta/20 text-brand-magenta text-[10px] px-1.5 py-0.5 rounded ml-2">
            Branch C
          </span>
        </button>
      ) : (
        <div className="bg-surface-container border border-brand-magenta/50 rounded-lg p-3 w-full sm:w-80 glow-magenta">
          {submitted ? (
            <div className="text-sm text-on-surface">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="w-2.5 h-2.5 rounded-full bg-brand-magenta"
                  aria-hidden
                />
                <span className="font-label text-brand-magenta">
                  Branch C queued
                </span>
              </div>
              <p className="text-caption text-on-surface-variant">
                What-if branches aren&apos;t simulated yet — your hypothetical is
                noted. Re-run the simulation with this assumption changed to see
                its effect.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSubmitted(false);
                  setText("");
                  setOpen(false);
                }}
                className="mt-2 text-xs text-on-surface-variant hover:text-on-surface"
              >
                Close
              </button>
            </div>
          ) : (
            <>
              <label className="flex items-center gap-2 font-label text-label text-brand-magenta mb-2">
                <Icon name="alt_route" className="text-[16px]" />
                Ask a what-if (Branch C)
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={2}
                placeholder="e.g. What if my partner supported the move?"
                className="w-full bg-surface-container-low border border-surface-variant rounded px-2.5 py-2 text-sm text-on-surface focus-ring placeholder:text-outline-variant resize-none"
              />
              <div className="flex gap-2 mt-2">
                <button
                  type="button"
                  disabled={!text.trim()}
                  onClick={() => setSubmitted(true)}
                  className="flex-1 bg-brand-magenta/20 border border-brand-magenta text-brand-magenta rounded px-3 py-1.5 text-sm font-medium hover:bg-brand-magenta/30 transition-colors disabled:opacity-50 focus-ring"
                >
                  Queue Branch C
                </button>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="text-on-surface-variant hover:text-on-surface text-sm px-2"
                >
                  Cancel
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
