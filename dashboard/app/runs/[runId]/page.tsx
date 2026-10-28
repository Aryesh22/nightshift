import React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllRunIds, getNormalizedReport } from "@/lib/report/load";
import { FindingCard } from "@/components/FindingCard";
import { SampleBanner, AiReviewedDisclaimer } from "@/components/Banner";
import { CostBar } from "@/components/CostBar";
import { Navbar } from "@/components/Navbar";
import { formatMoney } from "@/lib/report/format";
import { 
  ArrowUpRight, 
  Lock,
  ExternalLink
} from "lucide-react";

export function generateStaticParams() {
  const ids = getAllRunIds();
  return ids.map((runId) => ({ runId }));
}

interface PageProps {
  params: Promise<{ runId: string }>;
}

export default async function RunOverviewPage({ params }: PageProps) {
  const { runId } = await params;
  const report = getNormalizedReport(runId);

  if (!report) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-[#f1f5f9] dark:bg-[#0b0f17] text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors">
      {/* Top Navigation */}
      <Navbar
        breadcrumbs={[
          { label: "runs", href: "/" },
          { label: report.library.name },
        ]}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-8 w-full space-y-8">
        {report.isSample && <SampleBanner />}
        <AiReviewedDisclaimer />

        {/* Header Metadata Card */}
        <div className="border border-slate-200/90 dark:border-slate-800/80 rounded-xl p-6 bg-gradient-to-br from-white via-slate-50/40 to-sky-50/30 dark:bg-none dark:bg-[#111722] space-y-5 transition-colors shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100 tracking-tight">
                  {report.library.name}
                </h1>
                <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-sky-50 dark:bg-slate-800 text-sky-800 dark:text-slate-300 border border-sky-200/80 dark:border-slate-700 font-semibold">
                  v{report.library.version}
                </span>
                <span className="text-xs font-mono uppercase px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-slate-800 text-indigo-800 dark:text-slate-300 border border-indigo-200/80 dark:border-slate-700 font-semibold">
                  mode: {report.mode}
                </span>
                {report.airgapped && (
                  <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/20 flex items-center gap-1 font-semibold">
                    <Lock className="w-3 h-3" />
                    airgapped
                  </span>
                )}
              </div>
              <div className="text-xs font-mono text-slate-500 flex flex-wrap items-center gap-3">
                <span>run id: <code className="text-slate-800 dark:text-slate-200">{report.runId}</code></span>
                <span>•</span>
                <span>timestamp: {report.createdAt}</span>
                {report.library.repo && (
                  <>
                    <span>•</span>
                    <a
                      href={report.library.repo}
                      target="_blank"
                      rel="noreferrer"
                      className="text-slate-600 dark:text-slate-400 hover:text-sky-600 dark:hover:text-sky-400 underline underline-offset-2 flex items-center gap-1"
                    >
                      upstream repo <ExternalLink className="w-3 h-3" />
                    </a>
                  </>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2.5 shrink-0">
              <Link
                href={`/runs/${report.runId}/rejected`}
                className="px-3.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-mono transition shadow-xs font-medium"
              >
                Rejected ({report.statusCounts.rejected})
              </Link>
              <Link
                href={`/runs/${report.runId}/cost`}
                className="px-3.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-mono transition inline-flex items-center gap-1.5 shadow-xs font-medium"
              >
                Cost Ledger
                <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
              </Link>
            </div>
          </div>

          {/* Verification Funnel Bar */}
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider block mb-2 font-semibold">
              Verification Funnel &amp; Survivorship
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2.5 text-xs font-mono">
              <div className="p-3 rounded-lg border border-blue-200/80 dark:border-slate-800 bg-blue-50/50 dark:bg-[#0b0f17]/70">
                <span className="text-[10px] text-blue-800 dark:text-slate-500 block uppercase font-semibold">Candidates</span>
                <span className="text-base font-bold text-slate-900 dark:text-slate-100">{report.funnel.candidates}</span>
              </div>
              <div className="p-3 rounded-lg border border-emerald-500/30 dark:border-emerald-500/20 bg-emerald-50/70 dark:bg-emerald-500/5">
                <span className="text-[10px] text-emerald-800 dark:text-emerald-400 block uppercase font-semibold">Human Validated</span>
                <span className="text-base font-bold text-emerald-700 dark:text-emerald-400">{report.funnel.humanValidated}</span>
              </div>
              <div className="p-3 rounded-lg border border-violet-200/80 dark:border-slate-700 bg-violet-50/50 dark:bg-slate-800/60">
                <span className="text-[10px] text-violet-800 dark:text-slate-300 block uppercase font-semibold">AI-Reviewed</span>
                <span className="text-base font-bold text-slate-900 dark:text-slate-100">{report.funnel.aiReviewed}</span>
              </div>
              <div className="p-3 rounded-lg border border-amber-200/80 dark:border-slate-800 bg-amber-50/50 dark:bg-[#0b0f17]/70">
                <span className="text-[10px] text-amber-800 dark:text-slate-400 block uppercase font-semibold">Unresolved</span>
                <span className="text-base font-bold text-amber-800 dark:text-slate-300">{report.funnel.unresolved}</span>
              </div>
              <div className="p-3 rounded-lg border border-rose-200/80 dark:border-slate-800 bg-rose-50/50 dark:bg-[#0b0f17]/70">
                <span className="text-[10px] text-rose-800 dark:text-slate-500 block uppercase font-semibold line-through">Rejected</span>
                <span className="text-base font-bold text-rose-700 dark:text-slate-500">{report.funnel.rejected}</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-[#0b0f17]/70">
                <span className="text-[10px] text-slate-600 dark:text-slate-500 block uppercase font-semibold">Infra Fails</span>
                <span className="text-base font-bold text-slate-600 dark:text-slate-500">{report.stats.infraFailures}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Work Done & Campaign Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 text-xs font-mono">
          <div className="border border-indigo-200/70 dark:border-slate-800/80 rounded-xl p-4 bg-gradient-to-br from-white to-indigo-50/30 dark:bg-none dark:bg-[#111722] shadow-xs space-y-1">
            <span className="text-[11px] text-indigo-800 dark:text-slate-500 uppercase block font-semibold">Contracts Derived</span>
            <span className="text-base font-bold text-indigo-950 dark:text-slate-100">{report.stats.contracts}</span>
            <span className="text-[10px] text-slate-500 block">docs-first invariants</span>
          </div>
          <div className="border border-sky-200/70 dark:border-slate-800/80 rounded-xl p-4 bg-gradient-to-br from-white to-sky-50/30 dark:bg-none dark:bg-[#111722] shadow-xs space-y-1">
            <span className="text-[11px] text-sky-800 dark:text-slate-500 uppercase block font-semibold">Hypothesis Campaigns</span>
            <span className="text-base font-bold text-sky-950 dark:text-slate-100">{report.stats.campaigns}</span>
            <span className="text-[10px] text-slate-500 block">generators evaluated</span>
          </div>
          <div className="border border-teal-200/70 dark:border-slate-800/80 rounded-xl p-4 bg-gradient-to-br from-white to-teal-50/30 dark:bg-none dark:bg-[#111722] shadow-xs space-y-1">
            <span className="text-[11px] text-teal-800 dark:text-slate-500 uppercase block font-semibold">Assertions Run</span>
            <span className="text-base font-bold text-teal-950 dark:text-slate-100">
              {report.stats.assertionsRun ? report.stats.assertionsRun.toLocaleString() : "n/a"}
            </span>
            <span className="text-[10px] text-slate-500 block">total contract checks</span>
          </div>
          <div className="border border-amber-200/70 dark:border-slate-800/80 rounded-xl p-4 bg-gradient-to-br from-white to-amber-50/30 dark:bg-none dark:bg-[#111722] shadow-xs space-y-1">
            <span className="text-[11px] text-amber-800 dark:text-slate-500 uppercase block font-semibold">Tavily Credits Used</span>
            <span className="text-base font-bold text-amber-950 dark:text-slate-100">{report.tavily.creditsUsed}</span>
            <span className="text-[10px] text-slate-500 block">docs &amp; issue queries</span>
          </div>
        </div>

        {/* Cost Summary Bar */}
        <CostBar
          confirmedUsd={report.cost.confirmedUsd}
          pendingUsd={report.cost.pendingUsd}
          byModel={report.cost.byModel}
        />

        {/* Findings List Section */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-xs font-mono uppercase tracking-wider text-slate-700 dark:text-slate-300 font-semibold">
                Finding Cards ({report.findings.length})
              </h2>
              <p className="text-xs text-slate-500">
                Each card below is systematically structured to answer the 5 core evaluation questions.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono">
              <Link
                href={`/runs/${report.runId}/rejected`}
                className="text-slate-600 dark:text-slate-400 hover:text-sky-600 dark:hover:text-sky-400 underline underline-offset-2"
              >
                view rejected &amp; unresolved ({report.rejectedFindings.length + report.unresolvedFindings.length}) →
              </Link>
            </div>
          </div>

          {/* Cards */}
          <div className="space-y-6">
            {report.findings.map((finding) => (
              <FindingCard
                key={finding.id}
                finding={finding}
                runId={report.runId}
                runRejectedCost={report.cost.rejectedCandidatesCost}
                isDetailed={false}
              />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
