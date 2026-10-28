import React from "react";
import Link from "next/link";
import { getAllRunSummaries, getBenchmarkData } from "@/lib/report/load";
import { formatMoney } from "@/lib/report/format";
import { Navbar } from "@/components/Navbar";
import { ReportDropzone } from "@/components/ReportDropzone";
import { ArrowUpRight } from "lucide-react";

export default function HomePage() {
  const runs = getAllRunSummaries();
  const bench = getBenchmarkData();

  return (
    <div className="min-h-screen bg-[#f1f5f9] dark:bg-[#0b0f17] text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors">
      {/* Top Navigation */}
      <Navbar />

      {/* Main Container */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-8 w-full space-y-8">
        {/* Intro Banner */}
        <div className="border border-sky-200/70 dark:border-slate-800/80 bg-gradient-to-r from-sky-50/70 via-indigo-50/30 to-blue-50/40 dark:bg-none dark:bg-[#111722] rounded-xl p-6 transition-colors shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100 font-mono flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
                Contract-First Property Testing &amp; Detective Triage
              </h1>
              <p className="text-xs text-slate-600 dark:text-slate-400 max-w-2xl leading-relaxed font-sans">
                Nightshift derives invariant contracts from documentation alone, runs Hypothesis generator campaigns,
                attempts to disprove anomalies through fresh-process replays and refutation checks, and preserves verifiable evidence.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono shrink-0">
              <span className="px-2.5 py-1 rounded-md border border-indigo-200/80 dark:border-slate-800 bg-indigo-50/80 dark:bg-slate-900/60 text-indigo-800 dark:text-slate-300 shadow-2xs font-medium">
                mode: core
              </span>
              <span className="px-2.5 py-1 rounded-md border border-emerald-200/80 dark:border-slate-800 bg-emerald-50/80 dark:bg-slate-900/60 text-emerald-800 dark:text-slate-300 shadow-2xs font-medium">
                airgapped: on
              </span>
            </div>
          </div>
        </div>

        {/* Drag & Drop Report Inspector */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase tracking-wider text-slate-600 dark:text-slate-400 font-semibold">
              Inspect Custom Report (Live Client-Side Parsing)
            </h2>
            <span className="text-[11px] font-mono text-slate-500">
              Zero-server, 100% in-browser
            </span>
          </div>
          <ReportDropzone />
        </div>

        {/* Benchmark Quick Summary */}
        {bench && (
          <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl divide-y md:divide-y-0 md:divide-x divide-slate-200 dark:divide-slate-800 grid grid-cols-1 md:grid-cols-4 bg-white dark:bg-[#111722] font-mono text-xs transition-colors shadow-xs overflow-hidden">
            <div className="p-5 space-y-1 bg-emerald-50/50 dark:bg-transparent">
              <span className="text-[11px] text-emerald-800 dark:text-slate-500 uppercase tracking-wider block font-semibold">
                PBT-Bench Core
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                  {bench.summary.coreDetectedRatio}
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400">detected</span>
              </div>
              <span className="text-[11px] text-slate-600 dark:text-slate-500 block">7 of 10 tasks solved</span>
            </div>

            <div className="p-5 space-y-1 bg-slate-50/70 dark:bg-transparent">
              <span className="text-[11px] text-slate-600 dark:text-slate-500 uppercase tracking-wider block font-semibold">
                PBT-Bench Baseline
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-700 dark:text-slate-300">
                  {bench.summary.baselineDetectedRatio}
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400">detected</span>
              </div>
              <span className="text-[11px] text-slate-600 dark:text-slate-500 block">3 of 10 tasks solved (1 fail)</span>
            </div>

            <div className="p-5 space-y-1 bg-indigo-50/30 dark:bg-transparent">
              <span className="text-[11px] text-indigo-800 dark:text-slate-500 uppercase tracking-wider block font-semibold">
                Benchmark Spend
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  ${bench.summary.coreTotalCost.toFixed(2)}
                </span>
                <span className="text-xs text-slate-500">/ $10.00 cap</span>
              </div>
              <span className="text-[11px] text-slate-600 dark:text-slate-500 block">Mean ${(bench.summary.coreTotalCost / 10).toFixed(2)} / task</span>
            </div>

            <div className="p-5 flex flex-col justify-between bg-sky-50/30 dark:bg-transparent">
              <span className="text-[11px] text-sky-800 dark:text-slate-500 uppercase tracking-wider block font-semibold">
                Methodology
              </span>
              <Link 
                href="/benchmark" 
                className="text-xs font-semibold text-sky-700 dark:text-slate-300 hover:text-sky-800 dark:hover:text-sky-400 inline-flex items-center gap-1 mt-2 transition"
              >
                Inspect 20-run matrix <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}

        {/* Pre-Loaded Campaigns & Runs Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase tracking-wider text-slate-600 dark:text-slate-400 font-semibold">
              Pre-Loaded Campaigns &amp; Runs
            </h2>
            <span className="text-xs font-mono text-slate-500">
              {runs.length} {runs.length === 1 ? "run" : "runs"} indexed
            </span>
          </div>

          <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl divide-y divide-slate-200 dark:divide-slate-800 overflow-hidden bg-white dark:bg-[#111722] transition-colors shadow-xs">
            {runs.map((run) => (
              <div key={run.runId} className="p-5 bg-gradient-to-r from-white via-slate-50/40 to-sky-50/20 hover:from-sky-50/30 hover:to-indigo-50/20 dark:bg-none dark:bg-[#111722] dark:hover:bg-slate-800/40 transition">
                {run.isSample && (
                  <div className="mb-3.5 inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-amber-500/30 dark:border-amber-500/20 bg-amber-500/10 dark:bg-amber-500/5 text-amber-800 dark:text-amber-300 text-[11px] font-mono">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 dark:bg-amber-400"></span>
                    sample demonstration run (schema v1)
                  </div>
                )}

                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  {/* Package info */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-base font-bold text-slate-900 dark:text-slate-100">
                        {run.libraryName}
                      </span>
                      <span className="font-mono text-xs text-sky-800 dark:text-slate-400 px-2 py-0.5 rounded-md bg-sky-50 dark:bg-slate-800 border border-sky-200/80 dark:border-slate-700 font-semibold">
                        v{run.version}
                      </span>
                      <span className="font-mono text-xs text-indigo-800 dark:text-slate-400 px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-slate-800 border border-indigo-200/80 dark:border-slate-700 uppercase font-semibold">
                        {run.mode}
                      </span>
                    </div>
                    <div className="text-xs font-mono text-slate-500 flex items-center gap-2">
                      <span>id: {run.runId}</span>
                      <span>•</span>
                      <span>{run.createdAt}</span>
                    </div>
                  </div>

                  {/* Funnel summary */}
                  <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                    <span className="px-2.5 py-1 rounded-md bg-blue-50/70 dark:bg-slate-900 border border-blue-200/70 dark:border-slate-800 text-blue-800 dark:text-slate-400">
                      candidates: <strong className="text-slate-900 dark:text-slate-100">{run.totalFindings}</strong>
                    </span>
                    <span className="px-2.5 py-1 rounded-md bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-800 dark:text-emerald-300 font-medium">
                      human validated: <strong>{run.humanValidatedCount}</strong>
                    </span>
                    <span className="px-2.5 py-1 rounded-md bg-violet-50/70 dark:bg-slate-800/80 border border-violet-200/70 dark:border-slate-700 text-violet-800 dark:text-slate-300">
                      ai-reviewed: <strong>{run.aiReviewedCount}</strong>
                    </span>
                    <span className="px-2.5 py-1 rounded-md bg-amber-50/70 dark:bg-slate-900 border border-amber-200/70 dark:border-slate-800 text-amber-800 dark:text-slate-400">
                      unresolved: <strong>{run.unresolvedCount}</strong>
                    </span>
                    <span className="px-2.5 py-1 rounded-md bg-rose-50/70 dark:bg-slate-900 border border-rose-200/70 dark:border-slate-800 text-rose-700 dark:text-slate-500 line-through">
                      rejected: {run.rejectedCount}
                    </span>
                  </div>

                  {/* Cost & Action */}
                  <div className="flex items-center gap-4 self-end lg:self-center shrink-0">
                    <div className="text-right font-mono">
                      <span className="text-[11px] text-slate-500 block">confirmed</span>
                      <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                        {formatMoney(run.confirmedCostUsd)}
                      </span>
                    </div>
                    <Link
                      href={`/runs/${run.runId}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-sky-50/60 hover:border-sky-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-mono font-medium transition shadow-xs"
                    >
                      view report
                      <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer Note */}
        <div className="border-t border-slate-200 dark:border-slate-800/80 pt-6 text-[11px] font-mono text-slate-500 space-y-1">
          <p>
            <strong>Policy:</strong> Findings remain AI-reviewed candidates until independently reproduced by a person. 
            All rejected anomalies, unresolved leads, and spend ledgers remain fully visible.
          </p>
        </div>
      </main>
    </div>
  );
}
