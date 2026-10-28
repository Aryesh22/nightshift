import React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllRunIds, getNormalizedReport } from "@/lib/report/load";
import { FindingCard } from "@/components/FindingCard";
import { SampleBanner, AiReviewedDisclaimer } from "@/components/Banner";
import { Navbar } from "@/components/Navbar";

export function generateStaticParams() {
  const runIds = getAllRunIds();
  const params: { runId: string; id: string }[] = [];

  for (const runId of runIds) {
    const report = getNormalizedReport(runId);
    if (!report) continue;
    for (const f of report.findings) {
      params.push({ runId, id: f.id });
    }
  }

  return params;
}

interface PageProps {
  params: Promise<{ runId: string; id: string }>;
}

export default async function FindingDetailPage({ params }: PageProps) {
  const { runId, id } = await params;
  const report = getNormalizedReport(runId);

  if (!report) {
    notFound();
  }

  const finding = report.findings.find((f) => f.id === id);
  if (!finding) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-[#f1f5f9] dark:bg-[#0b0f17] text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors">
      {/* Top Navigation */}
      <Navbar
        breadcrumbs={[
          { label: "runs", href: "/" },
          { label: report.library.name, href: `/runs/${report.runId}` },
          { label: finding.id },
        ]}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-8 w-full space-y-6">
        {report.isSample && <SampleBanner />}
        <AiReviewedDisclaimer />

        {/* Detailed Finding View */}
        <FindingCard
          finding={finding}
          runId={report.runId}
          runRejectedCost={report.cost.rejectedCandidatesCost}
          isDetailed={true}
        />
      </main>
    </div>
  );
}
