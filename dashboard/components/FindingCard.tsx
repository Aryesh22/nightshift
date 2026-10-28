import React from "react";
import Link from "next/link";
import { NormalizedFinding } from "@/lib/report/normalize";
import { StatusBadge } from "./StatusBadge";
import { CodeBlock } from "./CodeBlock";
import { DiffBlock } from "./DiffBlock";
import { ReplayTable } from "./ReplayTable";
import { ToolCallTimeline } from "./ToolCallTimeline";
import { KnownIssueList } from "./KnownIssueList";
import { PatchCaveatBanner } from "./Banner";
import { formatMoney } from "@/lib/report/format";
import { ArrowUpRight, Sparkles, ExternalLink } from "lucide-react";

interface FindingCardProps {
  finding: NormalizedFinding;
  runId: string;
  runRejectedCost?: number;
  isDetailed?: boolean;
}

export function FindingCard({
  finding,
  runId,
  runRejectedCost = 0,
  isDetailed = false,
}: FindingCardProps) {
  return (
    <article className="border border-slate-200 dark:border-slate-800/80 rounded-xl overflow-hidden bg-white dark:bg-[#111722] font-mono text-xs space-y-0 transition-colors shadow-xs">
      {/* Finding Header */}
      <div className="border-b border-slate-200/90 dark:border-slate-800/80 p-4 sm:p-5 bg-gradient-to-r from-sky-50/40 via-slate-50/40 to-indigo-50/30 dark:bg-none dark:bg-slate-900/40 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-slate-500 font-mono text-xs">[{finding.id}]</span>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 tracking-tight font-sans">
              {finding.title}
            </h2>
          </div>
          <div className="text-[11px] text-slate-500 flex items-center gap-2">
            <span>contract: <code className="text-slate-800 dark:text-slate-300">{finding.contract.id}</code></span>
            <span>•</span>
            <span className="uppercase">family: {finding.contract.family}</span>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end md:self-auto shrink-0">
          <StatusBadge status={finding.status} />
          {!isDetailed && (
            <Link
              href={`/runs/${runId}/findings/${finding.id}`}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-mono transition shadow-xs"
            >
              details
              <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
            </Link>
          )}
        </div>
      </div>

      {/* The 5 Questions Container */}
      <div className="p-5 space-y-6">
        {/* Q1: What documented behaviour seems broken? */}
        <section className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-5 h-5 rounded-full border border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-300 flex items-center justify-center text-[10px] font-bold shadow-2xs">
              1
            </span>
            <h3 className="uppercase tracking-wider text-[11px] text-sky-950 dark:text-slate-200 font-semibold">
              What documented behaviour seems broken?
            </h3>
          </div>

          <div className="pl-7 space-y-2 font-sans">
            <div className="border border-sky-200/80 dark:border-slate-800 rounded-lg p-3.5 bg-sky-50/30 dark:bg-[#0b0f17]/60 space-y-1.5">
              <span className="font-mono text-[10px] uppercase text-sky-800 dark:text-slate-400 block font-semibold">
                Contract Claim ({finding.contract.family})
              </span>
              <p className="text-slate-800 dark:text-slate-200 text-xs leading-relaxed">
                {finding.contract.claim}
              </p>
            </div>

            {finding.contract.evidence.length > 0 && (
              <div className="border border-slate-200 dark:border-slate-800/80 rounded-lg p-3.5 bg-slate-50/70 dark:bg-[#0b0f17]/60 space-y-1.5">
                <span className="font-mono text-[10px] uppercase text-slate-500 block font-semibold">
                  Documentation Source &amp; Excerpt
                </span>
                <div className="space-y-1">
                  <a
                    href={finding.contract.evidence[0].source}
                    target="_blank"
                    rel="noreferrer"
                    className="font-mono text-[11px] text-slate-700 dark:text-slate-300 hover:text-sky-600 dark:hover:text-sky-400 underline underline-offset-2 flex items-center gap-1 truncate"
                  >
                    {finding.contract.evidence[0].source}
                    <ExternalLink className="w-3 h-3 text-slate-400 shrink-0" />
                  </a>
                  <p className="italic text-slate-700 dark:text-slate-300 text-xs border-l-2 border-sky-500 pl-2.5">
                    "{finding.contract.evidence[0].excerpt}"
                  </p>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Q2: Smallest repro we actually got */}
        <section className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-5 h-5 rounded-full border border-violet-300 bg-violet-50 text-violet-800 dark:border-violet-800 dark:bg-violet-950 dark:text-violet-300 flex items-center justify-center text-[10px] font-bold shadow-2xs">
              2
            </span>
            <h3 className="uppercase tracking-wider text-[11px] text-violet-950 dark:text-slate-200 font-semibold">
              Smallest repro we actually got
            </h3>
          </div>

          <div className="pl-7 space-y-3">
            <CodeBlock
              code={finding.repro}
              language="python"
              title="Reduced Repro Script"
              showLineNumbers
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Failing Output */}
              <div className="border border-rose-300/80 dark:border-rose-500/20 rounded-lg p-3 bg-rose-50/70 dark:bg-[#0b0f17]/60 space-y-1">
                <span className="text-[10px] uppercase text-rose-800 dark:text-rose-400 font-mono font-semibold block">
                  Failing Output (Actual)
                </span>
                <code className="text-slate-900 dark:text-slate-200 text-xs break-all block">
                  {finding.actual || "Assertion violation"}
                </code>
              </div>

              {/* Passing Control Input */}
              <div className="border border-emerald-300/80 dark:border-emerald-500/20 rounded-lg p-3 bg-emerald-50/70 dark:bg-[#0b0f17]/60 space-y-1">
                <span className="text-[10px] uppercase text-emerald-800 dark:text-emerald-400 font-mono font-semibold block">
                  Passing Control Input
                </span>
                <code className="text-slate-900 dark:text-slate-200 text-xs break-all block">
                  {finding.control || "Nearby valid input passes without error"}
                </code>
              </div>
            </div>
          </div>
        </section>

        {/* Q3: Checks that tried to disprove it */}
        <section className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-5 h-5 rounded-full border border-teal-300 bg-teal-50 text-teal-800 dark:border-teal-800 dark:bg-teal-950 dark:text-teal-300 flex items-center justify-center text-[10px] font-bold shadow-2xs">
              3
            </span>
            <h3 className="uppercase tracking-wider text-[11px] text-teal-950 dark:text-slate-200 font-semibold">
              Checks that tried to disprove it
            </h3>
          </div>

          <div className="pl-7 space-y-3">
            <ReplayTable
              passed={finding.replays.passed}
              attempted={finding.replays.attempted}
              rate={finding.replays.rate}
            />

            <ToolCallTimeline checks={finding.checks} />

            {/* Known issues search result */}
            {finding.knownBehaviour && (
              <KnownIssueList knownBehaviour={finding.knownBehaviour} />
            )}
          </div>
        </section>

        {/* Q4: Status and uncertainty */}
        <section className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-5 h-5 rounded-full border border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300 flex items-center justify-center text-[10px] font-bold shadow-2xs">
              4
            </span>
            <h3 className="uppercase tracking-wider text-[11px] text-amber-950 dark:text-slate-200 font-semibold">
              Status and uncertainty
            </h3>
          </div>

          <div className="pl-7 space-y-2 font-sans">
            <div className="border border-slate-200 dark:border-slate-800 rounded-lg p-3.5 bg-slate-50/70 dark:bg-[#0b0f17]/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-slate-500 text-xs">Current Status:</span>
                <StatusBadge status={finding.status} />
              </div>
              <span className="font-mono text-slate-500 text-[11px]">
                replays: {finding.replays.rate}
              </span>
            </div>

            {finding.uncertainty && (
              <div className="border border-amber-200/90 dark:border-slate-800/80 rounded-lg p-3.5 bg-amber-50/50 dark:bg-[#0b0f17]/40 text-xs space-y-1">
                <span className="font-mono text-[10px] uppercase text-amber-800 dark:text-slate-400 block font-semibold">
                  Still Unsure About:
                </span>
                <p className="text-amber-950 dark:text-slate-300 leading-relaxed">
                  {finding.uncertainty}
                </p>
              </div>
            )}

            {finding.rejectionReason && (
              <div className="border border-rose-300 dark:border-rose-500/25 bg-rose-50/60 dark:bg-rose-500/5 rounded-lg p-3.5 text-xs space-y-1">
                <span className="font-mono text-[10px] uppercase text-rose-700 dark:text-rose-400 block font-semibold">
                  Rejection Reason:
                </span>
                <p className="text-rose-900 dark:text-rose-200 leading-relaxed">
                  {finding.rejectionReason}
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Q5: Cost */}
        <section className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-5 h-5 rounded-full border border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 flex items-center justify-center text-[10px] font-bold shadow-2xs">
              5
            </span>
            <h3 className="uppercase tracking-wider text-[11px] text-emerald-950 dark:text-slate-200 font-semibold">
              Cost accounting
            </h3>
          </div>

          <div className="pl-7">
            <div className="border border-emerald-200/80 dark:border-slate-800 rounded-lg p-3.5 bg-emerald-50/30 dark:bg-[#0b0f17]/60 grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
              <div className="space-y-0.5">
                <span className="text-emerald-800 dark:text-slate-400 text-[10px] uppercase font-semibold">This Finding's Spend</span>
                <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {finding.cost.formatted}
                </div>
                <span className="text-[10px] text-slate-500">
                  {finding.routeTrace.length} stages (
                  {finding.routeTrace.map((s) => s.model).join(" → ") || "discovery"}
                  )
                </span>
              </div>

              <div className="space-y-0.5 sm:border-l sm:border-emerald-200/60 sm:dark:border-slate-800 sm:pl-3">
                <span className="text-slate-500 text-[10px] uppercase font-semibold">Run's Rejected Candidate Spend</span>
                <div className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                  {formatMoney(runRejectedCost)}
                </div>
                <span className="text-[10px] text-slate-500">
                  Total price includes testing disproven hypotheses
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Extras on detailed view: Patch & Ultra Review */}
        {isDetailed && (
          <div className="pt-4 border-t border-slate-200 dark:border-slate-800/80 space-y-4">
            {/* Proposed Patch if present */}
            {finding.patch.hasPatch && finding.patch.diff && (
              <div className="space-y-2">
                <span className="text-xs uppercase text-slate-700 dark:text-slate-300 tracking-wider font-semibold block">
                  Optional Candidate Patch
                </span>
                <PatchCaveatBanner />
                <DiffBlock diff={finding.patch.diff} />
                {finding.patch.validation && (
                  <div className="text-[11px] text-slate-600 dark:text-slate-400 font-sans p-3 rounded-lg bg-slate-50/70 dark:bg-[#0b0f17]/60 border border-slate-200 dark:border-slate-800">
                    <strong>Validation scope:</strong> {finding.patch.validation}
                  </div>
                )}
              </div>
            )}

            {/* Root Cause from Ultra Review if present */}
            {finding.rootCause && (
              <div className="border border-purple-200/80 dark:border-slate-800 rounded-lg p-3.5 bg-purple-50/40 dark:bg-[#0b0f17]/60 space-y-1">
                <span className="text-[10px] uppercase text-purple-800 dark:text-slate-300 font-mono font-semibold flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-purple-600 dark:text-slate-400" />
                  Ultra Review Root-Cause Analysis
                </span>
                <p className="text-purple-950 dark:text-slate-200 font-sans text-xs leading-relaxed">
                  {finding.rootCause}
                </p>
              </div>
            )}

            {/* Adapter approval & Wrapper hash */}
            {(finding.contract.adapterApproval || finding.contract.wrapperHash) && (
              <div className="border border-slate-200 dark:border-slate-800/80 rounded-lg p-3.5 bg-slate-50/70 dark:bg-[#0b0f17]/60 text-xs font-mono space-y-1.5 text-slate-600 dark:text-slate-400">
                <span className="text-[10px] uppercase text-slate-500 font-semibold block">
                  Core Contract Adapter &amp; Wrapper Receipt
                </span>
                {finding.contract.adapterApproval && (
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500">adapter approval:</span>
                    <span className="text-slate-800 dark:text-slate-200">{finding.contract.adapterApproval}</span>
                  </div>
                )}
                {finding.contract.wrapperHash && (
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500">wrapper hash:</span>
                    <code className="text-slate-800 dark:text-slate-200">{finding.contract.wrapperHash}</code>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
