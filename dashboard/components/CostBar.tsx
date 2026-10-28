import React from "react";
import { formatMoney } from "@/lib/report/format";

interface CostBarProps {
  confirmedUsd: number;
  pendingUsd?: number;
  budgetCapUsd?: number;
  byModel?: Record<string, number>;
}

export function CostBar({
  confirmedUsd,
  pendingUsd = 0,
  budgetCapUsd = 0.45,
  byModel = {},
}: CostBarProps) {
  const total = confirmedUsd + pendingUsd;
  const percentUsed = budgetCapUsd > 0 ? Math.min(100, (total / budgetCapUsd) * 100) : 0;

  return (
    <div className="border border-emerald-200/60 dark:border-slate-800/80 rounded-xl p-4 bg-gradient-to-r from-white via-slate-50/40 to-emerald-50/30 dark:bg-none dark:bg-[#111722] space-y-3 font-mono text-xs transition-colors shadow-xs">
      <div className="flex items-center justify-between text-slate-700 dark:text-slate-300">
        <div className="flex items-center gap-2">
          <span className="text-emerald-800 dark:text-slate-500 uppercase tracking-wider text-[11px] font-semibold">Run Spend</span>
          <span className="text-slate-900 dark:text-slate-100 font-bold">{formatMoney(confirmedUsd)}</span>
          {pendingUsd > 0 && (
            <span className="px-1.5 py-0.5 rounded-md border border-amber-500/30 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300 text-[10px]">
              +{formatMoney(pendingUsd)} pending
            </span>
          )}
        </div>
        <div className="text-slate-500 text-[11px]">
          Cap: {formatMoney(budgetCapUsd)} ({percentUsed.toFixed(0)}%)
        </div>
      </div>

      {/* Progress Track */}
      <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800/80 rounded-full overflow-hidden flex">
        <div
          className="bg-emerald-600 dark:bg-slate-300 h-full transition-all"
          style={{ width: `${Math.min(100, (confirmedUsd / budgetCapUsd) * 100)}%` }}
          title={`Confirmed: ${formatMoney(confirmedUsd)}`}
        />
        {pendingUsd > 0 && (
          <div
            className="bg-amber-500 dark:bg-amber-400/80 h-full transition-all"
            style={{ width: `${Math.min(100, (pendingUsd / budgetCapUsd) * 100)}%` }}
            title={`Pending/Estimated: ${formatMoney(pendingUsd)}`}
          />
        )}
      </div>

      {/* Model Breakdown */}
      {Object.keys(byModel).length > 0 && (
        <div className="pt-2 border-t border-slate-100 dark:border-slate-800/60 flex flex-wrap items-center gap-4 text-[11px] text-slate-500 dark:text-slate-400">
          <span className="text-slate-500 uppercase font-semibold">Tiers:</span>
          {Object.entries(byModel).map(([tier, cost]) => (
            <div key={tier} className="flex items-center gap-1.5">
              <span className="text-slate-600 dark:text-slate-400 capitalize">{tier}:</span>
              <span className="text-slate-900 dark:text-slate-200 font-medium">{formatMoney(cost)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
