import React from "react";
import { CheckCircle2, XCircle, RefreshCw } from "lucide-react";

interface ReplayTableProps {
  passed: number;
  attempted: number;
  rate: string;
}

export function ReplayTable({ passed, attempted, rate }: ReplayTableProps) {
  const replays = Array.from({ length: Math.max(3, attempted) }, (_, i) => {
    const isAttempted = i < attempted;
    const isPassed = i < passed;
    return {
      index: i + 1,
      attempted: isAttempted,
      passed: isPassed,
    };
  });

  const isSolid = attempted >= 3 && passed === attempted;

  return (
    <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl p-3.5 bg-slate-50/70 dark:bg-[#0b0f17]/70 font-mono text-xs space-y-2.5 transition-colors shadow-2xs">
      <div className="flex items-center justify-between text-slate-700 dark:text-slate-300">
        <span className="text-[11px] uppercase tracking-wider text-slate-500 flex items-center gap-1.5 font-semibold">
          <RefreshCw className="w-3 h-3 text-slate-400" />
          Fresh-Process Replay Runs
        </span>
        <span className={`text-[11px] px-2 py-0.5 rounded-md border ${
          isSolid
            ? "border-emerald-500/30 dark:border-emerald-500/20 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 font-medium"
            : "border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
        }`}>
          {rate} reproduced
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-1">
        {replays.map((r) => (
          <div
            key={r.index}
            className={`border rounded-lg p-2.5 flex items-center justify-between transition-colors shadow-2xs ${
              r.attempted
                ? r.passed
                  ? "border-emerald-500/30 dark:border-emerald-500/20 bg-white dark:bg-[#111722] text-emerald-700 dark:text-emerald-400"
                  : "border-rose-500/30 dark:border-rose-500/20 bg-white dark:bg-[#111722] text-rose-700 dark:text-rose-400"
                : "border-slate-200 dark:border-slate-800 bg-slate-100/60 dark:bg-slate-900/40 text-slate-400 dark:text-slate-600"
            }`}
          >
            <span className="text-[11px] font-medium">Run #{r.index}</span>
            {r.attempted ? (
              r.passed ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
              )
            ) : (
              <span className="text-[10px] text-slate-400 dark:text-slate-600">—</span>
            )}
          </div>
        ))}
      </div>
      <p className="text-[11px] text-slate-500 font-sans leading-relaxed">
        Each replay runs in a separate clean Python process to eliminate state contamination.
      </p>
    </div>
  );
}
