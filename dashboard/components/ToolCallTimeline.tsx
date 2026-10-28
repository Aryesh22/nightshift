"use client";

import React from "react";
import { NormalizedCheck } from "@/lib/report/normalize";
import { CheckCircle2, XCircle, MinusCircle } from "lucide-react";

interface ToolCallTimelineProps {
  checks: NormalizedCheck[];
  title?: string;
}

function CheckResultView({ rawResult }: { rawResult: string }) {
  const [showRaw, setShowRaw] = React.useState(false);

  let parsed: any = null;
  if (typeof rawResult === "string" && rawResult.trim().startsWith("{")) {
    try {
      parsed = JSON.parse(rawResult);
    } catch {
      parsed = null;
    }
  }

  if (!parsed || typeof parsed !== "object") {
    return (
      <p className="leading-relaxed text-slate-700 dark:text-slate-300 pt-0.5">
        {rawResult}
      </p>
    );
  }

  return (
    <div className="space-y-2 pt-1 font-sans text-xs">
      {/* Doc & Source Inspection */}
      {parsed.docstring && (
        <div className="bg-slate-50 dark:bg-[#0b0f17]/60 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] text-slate-500">
            {parsed.symbol && <span>symbol: <strong className="text-slate-700 dark:text-slate-300">{parsed.symbol}</strong></span>}
            {parsed.path && <span>path: <strong className="text-slate-700 dark:text-slate-300">{parsed.path}</strong></span>}
            {parsed.package_revision && <span>rev: <strong className="text-slate-700 dark:text-slate-300">{parsed.package_revision}</strong></span>}
          </div>
          <p className="text-slate-800 dark:text-slate-200 leading-relaxed italic">
            "{parsed.docstring}"
          </p>
          {parsed.source && (
            <details className="text-[11px] font-mono text-slate-500 pt-1">
              <summary className="cursor-pointer hover:text-slate-700 dark:hover:text-slate-300 select-none">
                view inspected source
              </summary>
              <pre className="mt-1.5 p-2 bg-slate-100 dark:bg-black/50 rounded text-slate-800 dark:text-slate-200 overflow-x-auto text-[10px] leading-tight">
                {parsed.source}
              </pre>
            </details>
          )}
        </div>
      )}

      {/* Execution / Control input run */}
      {(parsed.execution || parsed.kind || parsed.reach_rate !== undefined) && (
        <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
          {parsed.kind && (
            <span className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/20 font-medium">
              kind: {parsed.kind}
            </span>
          )}
          {parsed.execution?.status && (
            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
              exit: {parsed.execution.exit_code} ({parsed.execution.status})
            </span>
          )}
          {parsed.reach_rate !== undefined && (
            <span className="px-2 py-0.5 rounded bg-sky-50 dark:bg-sky-500/10 text-sky-800 dark:text-sky-300 border border-sky-200 dark:border-sky-500/20">
              reach: {(parsed.reach_rate * 100).toFixed(0)}%
            </span>
          )}
          {parsed.stats?.assertion_reached !== undefined && (
            <span className="text-[10px] text-slate-500">
              assertions reached: {parsed.stats.assertion_reached}
            </span>
          )}
        </div>
      )}

      {/* Boundary / Known issue query */}
      {parsed.query && (
        <div className="text-[11px] font-mono text-slate-600 dark:text-slate-400">
          <span>searched: </span>
          <code className="bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-800 dark:text-slate-200">
            {parsed.query}
          </code>
          {parsed.outcome && <span className="ml-2 font-semibold">→ {parsed.outcome}</span>}
        </div>
      )}

      {/* Raw JSON toggle */}
      <div className="pt-0.5">
        <button
          type="button"
          onClick={() => setShowRaw(!showRaw)}
          className="text-[10px] font-mono text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 underline"
        >
          {showRaw ? "hide payload" : "view payload"}
        </button>
        {showRaw && (
          <pre className="mt-1.5 p-2 bg-slate-100 dark:bg-black/60 rounded text-slate-700 dark:text-slate-300 font-mono text-[10px] overflow-x-auto">
            {JSON.stringify(parsed, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

export function ToolCallTimeline({ checks, title = "Refutation Checklist & Investigator Checks" }: ToolCallTimelineProps) {
  if (!checks || checks.length === 0) {
    return (
      <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl p-3 bg-white dark:bg-[#111722] text-xs font-mono text-slate-500">
        No investigator tool checks recorded for this finding.
      </div>
    );
  }

  const getEffectIcon = (effect: string) => {
    switch (effect.toLowerCase()) {
      case "supports":
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />;
      case "refutes":
        return <XCircle className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />;
      default:
        return <MinusCircle className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const getEffectBadge = (effect: string) => {
    switch (effect.toLowerCase()) {
      case "supports":
        return (
          <span className="px-2 py-0.5 rounded-md border border-emerald-500/30 dark:border-emerald-500/20 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 text-[10px] uppercase font-mono font-medium">
            supports finding
          </span>
        );
      case "refutes":
        return (
          <span className="px-2 py-0.5 rounded-md border border-rose-500/30 dark:border-rose-500/20 bg-rose-50 dark:bg-rose-500/10 text-rose-800 dark:text-rose-300 text-[10px] uppercase font-mono font-medium">
            refutes finding
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-md border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[10px] uppercase font-mono">
            neutral
          </span>
        );
    }
  };

  return (
    <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl overflow-hidden bg-white dark:bg-[#111722] font-mono text-xs transition-colors shadow-2xs">
      <div className="border-b border-slate-200 dark:border-slate-800/80 px-3.5 py-2.5 bg-slate-50/80 dark:bg-slate-900/40 flex items-center justify-between text-slate-700 dark:text-slate-300">
        <span className="font-semibold text-[11px] uppercase tracking-wider">{title}</span>
        <span className="text-slate-500 text-[11px]">{checks.length} checks performed</span>
      </div>

      <div className="divide-y divide-slate-100 dark:divide-slate-800/60">
        {checks.map((ck, idx) => (
          <div key={idx} className="p-3.5 space-y-2 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                {getEffectIcon(ck.effect)}
                <span className="text-slate-900 dark:text-slate-100 font-medium">{ck.question}</span>
              </div>
              {getEffectBadge(ck.effect)}
            </div>

            <div className="pl-5 space-y-1 text-slate-600 dark:text-slate-400 font-sans text-xs">
              <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500">
                <span>tool:</span>
                <code className="text-slate-800 dark:text-slate-200 bg-slate-50 dark:bg-[#0b0f17] px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-800">
                  {ck.tool}
                </code>
              </div>
              <CheckResultView rawResult={ck.result} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
