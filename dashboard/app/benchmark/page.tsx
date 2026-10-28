import React from "react";
import Link from "next/link";
import { getBenchmarkData } from "@/lib/report/load";
import { formatMoney } from "@/lib/report/format";
import { Navbar } from "@/components/Navbar";
import { 
  CheckCircle2, 
  XCircle, 
  Gauge, 
  ShieldCheck
} from "lucide-react";

export default function BenchmarkPage() {
  const bench = getBenchmarkData();

  if (!bench) {
    return (
      <div className="min-h-screen bg-[#f8fafc] dark:bg-[#0b0f17] text-slate-900 dark:text-slate-100 p-8 font-mono text-xs">
        No benchmark data found in data/benchmark/results.json.
      </div>
    );
  }

  const { config, summary, tasks } = bench;

  return (
    <div className="min-h-screen bg-[#f1f5f9] dark:bg-[#0b0f17] text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors">
      {/* Top Navigation */}
      <Navbar
        breadcrumbs={[
          { label: "runs", href: "/" },
          { label: "benchmark (pbt-bench)" },
        ]}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-8 w-full space-y-8">
        {/* Benchmark Header */}
        <div className="border border-sky-200/70 dark:border-slate-800/80 rounded-xl p-6 bg-gradient-to-r from-white via-slate-50/40 to-sky-50/30 dark:bg-none dark:bg-[#111722] space-y-2 transition-colors shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <h1 className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                <Gauge className="w-4 h-4 text-sky-600 dark:text-sky-500" />
                PBT-Bench Evaluation: Nightshift Core vs Baseline
              </h1>
              <p className="text-xs text-slate-600 dark:text-slate-400 font-sans leading-relaxed max-w-3xl">
                A 20-campaign head-to-head comparison across 10 matched PBT-Bench tasks (4 L1, 4 L2, 2 L3).
                Tasks were evaluated under frozen budget caps, airgapped documentation, and interleaved campaign order.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono shrink-0">
              <span className="px-2.5 py-1 rounded-md border border-indigo-200/80 dark:border-slate-800 bg-indigo-50/70 dark:bg-slate-900/60 text-indigo-800 dark:text-slate-300 shadow-2xs font-semibold">
                total budget: $10.00
              </span>
              <span className="px-2.5 py-1 rounded-md border border-emerald-200/80 dark:border-slate-800 bg-emerald-50/70 dark:bg-slate-900/60 text-emerald-800 dark:text-slate-300 shadow-2xs font-semibold">
                cap/run: $0.45
              </span>
            </div>
          </div>
        </div>

        {/* Head-to-Head Comparison Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 font-mono text-xs">
          {/* Nightshift Core Card */}
          <div className="border border-emerald-500/30 dark:border-emerald-500/20 rounded-xl p-6 bg-gradient-to-br from-white to-emerald-50/40 dark:bg-none dark:bg-[#111722] space-y-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wider text-emerald-700 dark:text-emerald-400 font-semibold flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4" />
                Nightshift (Core Mode)
              </span>
              <span className="text-[10px] text-emerald-800 dark:text-slate-400 uppercase px-2 py-0.5 rounded-md border border-emerald-200 dark:border-slate-800 bg-emerald-50 dark:bg-slate-900/60 font-semibold">
                contract-first
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2.5 pt-1">
              <div className="p-3 rounded-lg border border-emerald-500/30 dark:border-emerald-500/20 bg-emerald-50/60 dark:bg-emerald-500/5">
                <span className="text-[10px] text-emerald-800 dark:text-slate-500 uppercase block font-semibold">Detection</span>
                <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 block mt-0.5">
                  {summary.coreDetectedRatio}
                </span>
                <span className="text-[10px] text-slate-500">7 of 10 tasks</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-[#0b0f17]/70">
                <span className="text-[10px] text-slate-500 uppercase block font-semibold">Total Spend</span>
                <span className="text-2xl font-bold text-slate-900 dark:text-slate-100 block mt-0.5">
                  ${summary.coreTotalCost.toFixed(2)}
                </span>
                <span className="text-[10px] text-slate-500">under $10 cap</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-[#0b0f17]/70">
                <span className="text-[10px] text-slate-500 uppercase block font-semibold">Failures</span>
                <span className="text-2xl font-bold text-slate-900 dark:text-slate-100 block mt-0.5">
                  {summary.coreFailures}
                </span>
                <span className="text-[10px] text-slate-500">0 timeouts</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-600 dark:text-slate-400 font-sans leading-relaxed">
              Hypothesis generator strategies derived from docs-first contracts. Super investigator checked refutations 
              and eliminated bogus test candidates before reporting.
            </p>
          </div>

          {/* Baseline Card */}
          <div className="border border-slate-200/90 dark:border-slate-800/80 rounded-xl p-6 bg-gradient-to-br from-white to-slate-50/60 dark:bg-none dark:bg-[#111722] space-y-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wider text-slate-700 dark:text-slate-300 font-semibold">
                Baseline Pipeline
              </span>
              <span className="text-[10px] text-slate-500 uppercase px-2 py-0.5 rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 font-semibold">
                passive judge
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2.5 pt-1">
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-[#0b0f17]/70">
                <span className="text-[10px] text-slate-500 uppercase block font-semibold">Detection</span>
                <span className="text-2xl font-bold text-slate-700 dark:text-slate-300 block mt-0.5">
                  {summary.baselineDetectedRatio}
                </span>
                <span className="text-[10px] text-slate-500">3 of 10 tasks</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-[#0b0f17]/70">
                <span className="text-[10px] text-slate-500 uppercase block font-semibold">Total Spend</span>
                <span className="text-2xl font-bold text-slate-900 dark:text-slate-100 block mt-0.5">
                  ${summary.baselineTotalCost.toFixed(2)}
                </span>
                <span className="text-[10px] text-slate-500">under $10 cap</span>
              </div>
              <div className="p-3 rounded-lg border border-rose-200/80 dark:border-slate-800 bg-rose-50/40 dark:bg-[#0b0f17]/70">
                <span className="text-[10px] text-rose-800 dark:text-slate-500 uppercase block font-semibold">Failures</span>
                <span className="text-2xl font-bold text-rose-600 dark:text-rose-400 block mt-0.5">
                  {summary.baselineFailures}
                </span>
                <span className="text-[10px] text-rose-600/80 dark:text-rose-400/80">1 harness timeout</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-600 dark:text-slate-400 font-sans leading-relaxed">
              Original prompt-based generator pipeline with passive triage judge. Prone to test code duplication
              and hallucinations without contracts.
            </p>
          </div>
        </div>

        {/* Per-Task Head-to-Head Matrix */}
        <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl overflow-hidden bg-white dark:bg-[#111722] font-mono text-xs transition-colors shadow-xs">
          <div className="border-b border-slate-200 dark:border-slate-800/80 px-5 py-3 bg-slate-50/70 dark:bg-slate-900/40 flex items-center justify-between text-slate-700 dark:text-slate-300">
            <span className="font-semibold text-[11px] uppercase tracking-wider">
              Per-Task Results Matrix (10 Tasks × 2 Variants)
            </span>
            <span className="text-slate-500 text-[11px]">Interleaved execution order</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20 text-slate-500 text-[11px] uppercase">
                  <th className="p-3.5 font-semibold">Task ID</th>
                  <th className="p-3.5 font-semibold">Level</th>
                  <th className="p-3.5 font-semibold">Baseline Detected</th>
                  <th className="p-3.5 font-semibold">Baseline Cost</th>
                  <th className="p-3.5 font-semibold">Core Detected</th>
                  <th className="p-3.5 font-semibold">Core Disproved</th>
                  <th className="p-3.5 font-semibold">Core Cost</th>
                  <th className="p-3.5 font-semibold">Comparison</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300">
                {tasks.map((t) => {
                  const coreWon = t.nightshiftCore.evaluatorDetected && !t.baseline.evaluatorDetected;
                  const tie = t.nightshiftCore.evaluatorDetected === t.baseline.evaluatorDetected;

                  return (
                    <tr key={t.taskId} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/30 transition">
                      <td className="p-3.5 font-semibold text-slate-900 dark:text-slate-100">
                        {t.taskId}
                      </td>
                      <td className="p-3.5">
                        <span className={`px-2 py-0.5 rounded-md border text-[10px] font-semibold ${
                          t.level === "L1"
                            ? "border-emerald-200/90 dark:border-emerald-500/20 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300"
                            : t.level === "L2"
                            ? "border-sky-200/90 dark:border-sky-500/20 bg-sky-50 dark:bg-sky-500/10 text-sky-800 dark:text-sky-300"
                            : "border-purple-200/90 dark:border-purple-500/20 bg-purple-50 dark:bg-purple-500/10 text-purple-800 dark:text-purple-300"
                        }`}>
                          {t.level}
                        </span>
                      </td>

                      {/* Baseline */}
                      <td className="p-3.5">
                        {t.baseline.status === "failed" ? (
                          <span className="text-rose-600 dark:text-rose-400 flex items-center gap-1 font-medium">
                            <XCircle className="w-3.5 h-3.5" /> fail
                          </span>
                        ) : t.baseline.evaluatorDetected ? (
                          <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5" /> yes
                          </span>
                        ) : (
                          <span className="text-slate-400 flex items-center gap-1">
                            <XCircle className="w-3.5 h-3.5" /> no
                          </span>
                        )}
                      </td>
                      <td className="p-3.5 text-slate-500 dark:text-slate-400">
                        {formatMoney(t.baseline.costUsd)}
                      </td>

                      {/* Core */}
                      <td className="p-3.5">
                        {t.nightshiftCore.evaluatorDetected ? (
                          <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> yes
                          </span>
                        ) : (
                          <span className="text-slate-400 flex items-center gap-1">
                            <XCircle className="w-3.5 h-3.5" /> no
                          </span>
                        )}
                      </td>
                      <td className="p-3.5 text-slate-500 dark:text-slate-400">
                        {t.nightshiftCore.findingsRejected} rejected
                      </td>
                      <td className="p-3.5 text-slate-900 dark:text-slate-100 font-medium">
                        {formatMoney(t.nightshiftCore.costUsd)}
                      </td>

                      {/* Winner */}
                      <td className="p-3.5">
                        {coreWon ? (
                          <span className="inline-flex px-2 py-0.5 rounded-md border border-emerald-300/80 dark:border-emerald-500/20 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 font-semibold text-[11px]">
                            Core won (+1)
                          </span>
                        ) : tie ? (
                          <span className="text-slate-400 text-[11px]">Tied</span>
                        ) : (
                          <span className="inline-flex px-2 py-0.5 rounded-md border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[11px]">
                            Baseline (+1)
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Methodology & Frozen Config Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 font-mono text-xs">
          {/* Methodology Panel */}
          <div className="border border-indigo-200/70 dark:border-slate-800/80 rounded-xl p-5 bg-gradient-to-br from-white to-indigo-50/25 dark:bg-none dark:bg-[#111722] space-y-3 shadow-xs">
            <span className="text-[11px] uppercase tracking-wider text-indigo-900 dark:text-slate-300 font-semibold block">
              Frozen Benchmark Configuration
            </span>
            <div className="space-y-2 text-slate-600 dark:text-slate-400 text-[11px]">
              <div>Commit SHA: <code className="text-slate-900 dark:text-slate-100">{config.commitSha}</code></div>
              <div>Seed: <code className="text-slate-900 dark:text-slate-100">{config.selectionRulesSeed}</code> (4 L1, 4 L2, 2 L3)</div>
              <div>Airgapped Mode: <code className="text-emerald-600 dark:text-emerald-400 font-medium">active</code> (no web retrieval leakage)</div>
              <div>Frozen Date: <code className="text-slate-700 dark:text-slate-300">{config.frozenDate}</code></div>
              <div>Models: Lightning (Nemotron-340B), Super (Nemotron-70B)</div>
            </div>
          </div>

          {/* Caveats Panel (Honesty Rules) */}
          <div className="border border-amber-200/70 dark:border-slate-800/80 rounded-xl p-5 bg-gradient-to-br from-white to-amber-50/25 dark:bg-none dark:bg-[#111722] space-y-3 shadow-xs">
            <span className="text-[11px] uppercase tracking-wider text-amber-900 dark:text-slate-300 font-semibold block">
              Scientific Caveats &amp; Disclosures
            </span>
            <div className="space-y-2 text-slate-600 dark:text-slate-400 text-[11px] font-sans leading-relaxed">
              <p>
                <strong>Sample Size:</strong> With n=10 tasks, results are strictly descriptive counts (7/10 vs 3/10).
                No claim of statistical significance or generalized benchmark dominance is made.
              </p>
              <p>
                <strong>Routing Policy Asymmetry:</strong> {config.asymmetryNote}
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
