import React from "react";
import { AlertTriangle, Info } from "lucide-react";

export function SampleBanner() {
  return (
    <div className="border border-amber-500/30 dark:border-amber-500/20 bg-amber-50/60 dark:bg-amber-500/5 px-4 py-3 rounded-xl flex items-center justify-between text-xs font-mono text-amber-900 dark:text-amber-300 transition-colors shadow-2xs">
      <div className="flex items-center gap-2.5">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 dark:bg-amber-400"></span>
        <span className="font-semibold uppercase tracking-wider">Sample Demonstration Run</span>
        <span className="text-slate-300 dark:text-slate-700">—</span>
        <span className="text-slate-600 dark:text-slate-400 font-sans">
          This run uses synthetic fixture data illustrating Schema v1. Real findings require human reproduction.
        </span>
      </div>
      <span className="text-[10px] uppercase tracking-wider text-amber-800 dark:text-amber-400 border border-amber-500/30 dark:border-amber-500/20 px-2 py-0.5 rounded-md font-mono bg-amber-100/50 dark:bg-amber-500/10">
        demo
      </span>
    </div>
  );
}

export function AiReviewedDisclaimer() {
  return (
    <div className="border border-sky-200/80 dark:border-slate-800/80 bg-sky-50/40 dark:bg-[#111722] px-4 py-3 rounded-xl flex items-start gap-2.5 text-xs text-slate-700 dark:text-slate-400 transition-colors shadow-xs">
      <Info className="w-4 h-4 text-sky-600 dark:text-slate-500 shrink-0 mt-0.5" />
      <div className="leading-relaxed">
        <strong className="text-slate-900 dark:text-slate-100 font-semibold">Candidate Reproduction Notice:</strong> Findings remain
        {" "}<span className="text-sky-900 dark:text-slate-200 font-mono font-medium bg-sky-100/60 dark:bg-slate-800 px-1.5 py-0.5 rounded">AI-reviewed candidates</span> until reproduced and validated 
        by a human against the pinned upstream repository.
      </div>
    </div>
  );
}

export function PatchCaveatBanner() {
  return (
    <div className="border border-slate-200 dark:border-slate-800/80 bg-slate-50/80 dark:bg-slate-900/40 p-3.5 rounded-xl text-xs space-y-1 transition-colors">
      <div className="flex items-center gap-1.5 font-mono text-slate-800 dark:text-slate-200 font-medium text-[11px] uppercase tracking-wider">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
        Patch Validation Scope
      </div>
      <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-[11px]">
        Checked strictly against the unchanged discovery test, reduced repro, protected file hashes, and a library-only diff policy.
        Hidden tests and the full upstream test suite were not evaluated.
      </p>
    </div>
  );
}
