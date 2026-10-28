import React from "react";
import { NormalizedEvidence } from "@/lib/report/normalize";
import { FileText, ExternalLink, ShieldCheck, AlertCircle } from "lucide-react";

interface DocEvidenceProps {
  evidence: NormalizedEvidence[];
  contractId: string;
  claim: string;
  family: string;
}

export function DocEvidence({
  evidence,
  contractId,
  claim,
  family,
}: DocEvidenceProps) {
  return (
    <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl overflow-hidden bg-white dark:bg-[#111722] font-mono text-xs space-y-0 transition-colors shadow-2xs">
      <div className="border-b border-slate-200 dark:border-slate-800/80 px-3.5 py-2.5 bg-slate-50/80 dark:bg-slate-900/40 flex items-center justify-between text-slate-700 dark:text-slate-300">
        <div className="flex items-center gap-2">
          <FileText className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-semibold text-[11px] uppercase tracking-wider">
            Documentation Evidence &amp; Invariant
          </span>
        </div>
        <span className="text-[11px] text-slate-600 dark:text-slate-400 uppercase px-2 py-0.5 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60">
          family: {family}
        </span>
      </div>

      <div className="p-4 space-y-3.5">
        {/* Frozen Contract Claim */}
        <div className="space-y-1">
          <span className="text-[11px] uppercase tracking-wider text-slate-500 block font-semibold">
            Contract Claim ({contractId})
          </span>
          <p className="font-sans text-xs text-slate-800 dark:text-slate-200 leading-relaxed bg-slate-50/70 dark:bg-[#0b0f17]/60 p-3 rounded-lg border border-slate-200 dark:border-slate-800/80">
            {claim}
          </p>
        </div>

        {/* Evidence Sources */}
        <div className="space-y-2 pt-1">
          <span className="text-[11px] uppercase tracking-wider text-slate-500 block font-semibold">
            Documented Sources &amp; Excerpts
          </span>

          {evidence.length === 0 ? (
            <div className="text-slate-500 italic text-[11px] p-2.5 bg-slate-50 dark:bg-slate-900/20 rounded-lg border border-slate-200 dark:border-slate-800/60">
              No direct documentation excerpts linked to this contract.
            </div>
          ) : (
            <div className="space-y-2.5">
              {evidence.map((ev, idx) => (
                <div
                  key={idx}
                  className="border border-slate-200 dark:border-slate-800/80 rounded-lg p-3 bg-slate-50/50 dark:bg-[#0b0f17]/40 space-y-2 shadow-2xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                    <div className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                      {ev.isPinnedCommit ? (
                        <span title="Pinned commit reference">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                        </span>
                      ) : (
                        <span title="Unpinned reference">
                          <AlertCircle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400/80" />
                        </span>
                      )}
                      <a
                        href={ev.source}
                        target="_blank"
                        rel="noreferrer"
                        className="text-slate-800 dark:text-slate-300 hover:text-sky-600 dark:hover:text-sky-400 underline underline-offset-2 flex items-center gap-1 truncate max-w-md"
                      >
                        {ev.source}
                        <ExternalLink className="w-3 h-3 text-slate-400 shrink-0" />
                      </a>
                    </div>
                    <div className="flex items-center gap-2">
                      {ev.contentHash && (
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono bg-slate-100 dark:bg-slate-900 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-800" title={ev.contentHash}>
                          {ev.contentHash.startsWith("sha256:") ? ev.contentHash.slice(7, 19) : ev.contentHash.slice(0, 12)}…
                        </span>
                      )}
                      <span className="text-slate-500 text-[10px]">
                        {ev.retrieved}
                      </span>
                    </div>
                  </div>

                  <blockquote className="font-sans text-xs text-slate-700 dark:text-slate-300 border-l-2 border-slate-300 dark:border-slate-700 pl-2.5 italic">
                    "{ev.excerpt}"
                  </blockquote>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
