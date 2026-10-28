import React from "react";
import { NormalizedKnownBehaviour } from "@/lib/report/normalize";
import { Search, ExternalLink } from "lucide-react";

interface KnownIssueListProps {
  knownBehaviour: NormalizedKnownBehaviour | null;
}

export function KnownIssueList({ knownBehaviour }: KnownIssueListProps) {
  if (!knownBehaviour) {
    return (
      <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl p-3.5 bg-slate-50/70 dark:bg-[#0b0f17]/70 font-mono text-xs text-slate-500">
        No known-issue search executed for this anomaly.
      </div>
    );
  }

  return (
    <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl p-3.5 bg-slate-50/70 dark:bg-[#0b0f17]/70 font-mono text-xs space-y-2.5 transition-colors shadow-2xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
            Known Issue Search (Tavily)
          </span>
        </div>
        <span className="text-[10px] text-slate-500 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 px-2 py-0.5 rounded-md font-mono">
          uncertain until applicability is checked
        </span>
      </div>

      <div className="bg-white dark:bg-[#111722] border border-slate-200 dark:border-slate-800/80 rounded-lg p-3 space-y-2">
        <div className="text-slate-900 dark:text-slate-100 font-semibold text-xs">
          {knownBehaviour.label}
        </div>

        {knownBehaviour.note && (
          <p className="text-slate-600 dark:text-slate-400 font-sans text-xs leading-relaxed">
            {knownBehaviour.note}
          </p>
        )}

        {knownBehaviour.links.length > 0 && (
          <div className="pt-1 space-y-1">
            <span className="text-[10px] uppercase text-slate-500 font-semibold block">Related References:</span>
            {knownBehaviour.links.map((link, idx) => (
              <a
                key={idx}
                href={link}
                target="_blank"
                rel="noreferrer"
                className="text-slate-800 dark:text-slate-200 hover:text-sky-600 dark:hover:text-sky-400 underline underline-offset-2 flex items-center gap-1 truncate text-[11px]"
              >
                {link}
                <ExternalLink className="w-3 h-3 text-slate-400 shrink-0" />
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
