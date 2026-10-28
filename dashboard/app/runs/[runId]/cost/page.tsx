import React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllRunIds, getNormalizedReport } from "@/lib/report/load";
import { SampleBanner } from "@/components/Banner";
import { Navbar } from "@/components/Navbar";
import { formatMoney, formatCredits } from "@/lib/report/format";
import { DollarSign, Search } from "lucide-react";

export function generateStaticParams() {
  const ids = getAllRunIds();
  return ids.map((runId) => ({ runId }));
}

interface PageProps {
  params: Promise<{ runId: string }>;
}

export default async function CostBreakdownPage({ params }: PageProps) {
  const { runId } = await params;
  const report = getNormalizedReport(runId);

  if (!report) {
    notFound();
  }

  const { cost, tavily, statusCounts } = report;

  return (
    <div className="min-h-screen bg-[#f1f5f9] dark:bg-[#0b0f17] text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors">
      {/* Top Navigation */}
      <Navbar
        breadcrumbs={[
          { label: "runs", href: "/" },
          { label: report.library.name, href: `/runs/${report.runId}` },
          { label: "cost & accounting" },
        ]}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-8 w-full space-y-8">
        {report.isSample && <SampleBanner />}

        {/* Header */}
        <div className="border border-blue-200/70 dark:border-slate-800/80 rounded-xl p-6 bg-gradient-to-r from-white via-slate-50/40 to-blue-50/30 dark:bg-none dark:bg-[#111722] space-y-2 transition-colors shadow-xs">
          <h1 className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-emerald-600 dark:text-slate-400" />
            Cost Accounting &amp; Cap Usage Ledger
          </h1>
          <p className="text-xs text-slate-600 dark:text-slate-400 font-sans leading-relaxed max-w-3xl">
            Nightshift maintains a strict dollar meter with hard per-run caps. Costs are split into confirmed spend
            and pending/estimated charges (such as ambiguous network retries or pending retrieval charges).
          </p>
        </div>

        {/* Spend Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono text-xs">
          <div className="border border-blue-200/80 dark:border-slate-800/80 rounded-xl p-5 bg-gradient-to-br from-white to-blue-50/40 dark:bg-none dark:bg-[#111722] space-y-1 shadow-xs">
            <span className="text-[11px] text-blue-800 dark:text-slate-500 uppercase tracking-wider block font-semibold">
              Confirmed Spend
            </span>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {formatMoney(cost.confirmedUsd)}
            </div>
            <span className="text-[10px] text-slate-500 block">Verified provider charges</span>
          </div>

          <div className="border border-amber-200/80 dark:border-slate-800/80 rounded-xl p-5 bg-gradient-to-br from-white to-amber-50/40 dark:bg-none dark:bg-[#111722] space-y-1 shadow-xs">
            <span className="text-[11px] text-amber-800 dark:text-slate-500 uppercase tracking-wider block font-semibold">
              Pending / Estimated
            </span>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {formatMoney(cost.pendingUsd)}
            </div>
            <span className="text-[10px] text-slate-500 block">
              {cost.pendingUsd > 0 ? "Ambiguous retries pending reconciliation" : "Zero pending charges"}
            </span>
          </div>

          <div className="border border-violet-200/80 dark:border-slate-800/80 rounded-xl p-5 bg-gradient-to-br from-white to-violet-50/40 dark:bg-none dark:bg-[#111722] space-y-1 shadow-xs">
            <span className="text-[11px] text-violet-800 dark:text-slate-500 uppercase tracking-wider block font-semibold">
              Cost / AI-Reviewed Finding
            </span>
            <div className="text-2xl font-bold text-slate-800 dark:text-slate-200">
              {formatMoney(cost.costPerAiReviewed)}
            </div>
            <span className="text-[10px] text-slate-500 block">
              Over {statusCounts.ai_reviewed + statusCounts.human_validated + statusCounts.maintainer_confirmed} candidates
            </span>
          </div>

          <div className="border border-emerald-200/80 dark:border-slate-800/80 rounded-xl p-5 bg-gradient-to-br from-white to-emerald-50/40 dark:bg-none dark:bg-[#111722] space-y-1 shadow-xs">
            <span className="text-[11px] text-emerald-800 dark:text-slate-500 uppercase tracking-wider block font-semibold">
              Cost / Human-Validated Finding
            </span>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {formatMoney(cost.costPerHumanValidated)}
            </div>
            <span className="text-[10px] text-slate-500 block">
              Over {statusCounts.human_validated + statusCounts.maintainer_confirmed} validated bugs
            </span>
          </div>
        </div>

        {/* Tier & Model Breakdown */}
        <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl overflow-hidden bg-white dark:bg-[#111722] font-mono text-xs transition-colors shadow-xs">
          <div className="border-b border-slate-200 dark:border-slate-800/80 px-5 py-3 bg-slate-50/70 dark:bg-slate-900/40 flex items-center justify-between text-slate-700 dark:text-slate-300">
            <span className="font-semibold text-[11px] uppercase tracking-wider">
              Spend by Model Tier
            </span>
            <span className="text-slate-500 text-[11px]">Core Role Architecture</span>
          </div>

          <div className="p-5 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              {/* Lightning */}
              <div className="border border-sky-200/80 dark:border-slate-800/80 rounded-lg p-3.5 bg-sky-50/40 dark:bg-[#0b0f17]/60 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-sky-950 dark:text-slate-200 font-semibold">Lightning</span>
                  <span className="text-sky-900 dark:text-slate-100 font-bold">{formatMoney(cost.byModel.lightning ?? 0)}</span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 font-sans">
                  Contract proposal &amp; Hypothesis strategy generation.
                </p>
              </div>

              {/* Super */}
              <div className="border border-indigo-200/80 dark:border-slate-800/80 rounded-lg p-3.5 bg-indigo-50/40 dark:bg-[#0b0f17]/60 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-indigo-950 dark:text-slate-200 font-semibold">Super</span>
                  <span className="text-indigo-900 dark:text-slate-100 font-bold">{formatMoney(cost.byModel.super ?? 0)}</span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 font-sans">
                  Investigator refutation checks &amp; adapter approval.
                </p>
              </div>

              {/* Ultra */}
              <div className="border border-violet-200/80 dark:border-slate-800/80 rounded-lg p-3.5 bg-violet-50/40 dark:bg-[#0b0f17]/60 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-violet-950 dark:text-slate-200 font-semibold">Ultra (Optional)</span>
                  <span className="text-violet-900 dark:text-slate-100 font-bold">{formatMoney(cost.byModel.ultra ?? 0)}</span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 font-sans">
                  Root-cause review &amp; candidate patch generation.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tavily Credits Usage */}
        <div className="border border-amber-200/70 dark:border-slate-800/80 rounded-xl p-5 bg-gradient-to-r from-white via-slate-50/40 to-amber-50/30 dark:bg-none dark:bg-[#111722] font-mono text-xs space-y-3 transition-colors shadow-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-800 dark:text-slate-200">
              <Search className="w-4 h-4 text-amber-600 dark:text-slate-400" />
              <span className="font-semibold uppercase tracking-wider text-[11px] text-amber-900 dark:text-slate-200">
                Tavily Search &amp; Extraction Credits
              </span>
            </div>
            <span className="text-amber-900 dark:text-slate-200 font-bold bg-amber-100/60 dark:bg-slate-800 px-2.5 py-0.5 rounded-md border border-amber-200 dark:border-slate-700">
              {formatCredits(tavily.creditsUsed)} credits used
            </span>
          </div>

          <div className="text-[11px] text-slate-600 dark:text-slate-400 font-sans leading-relaxed">
            Credits were allocated for versioned documentation retrieval and known-issue duplicate searches.
            Free-tier ceiling strictly observed; paid overage disabled.
          </div>
        </div>
      </main>
    </div>
  );
}
