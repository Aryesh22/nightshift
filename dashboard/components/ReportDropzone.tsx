"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, AlertCircle, X } from "lucide-react";
import { safeParseReport } from "@/lib/report/schema";
import { normalizeReport, NormalizedReport } from "@/lib/report/normalize";
import { FindingCard } from "./FindingCard";
import { CostBar } from "./CostBar";

export function ReportDropzone() {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedReport, setUploadedReport] = useState<NormalizedReport | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processJsonText = (text: string) => {
    setError(null);
    try {
      const parsed = JSON.parse(text);
      const validation = safeParseReport(parsed);

      if (!validation.success) {
        const issues = validation.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).slice(0, 3);
        setError(`Schema v1 validation error:\n${issues.join("\n")}`);
        return;
      }

      const normalized = normalizeReport(validation.data);
      setUploadedReport(normalized);
    } catch (err: any) {
      setError(`Failed to parse JSON file: ${err.message || String(err)}`);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (!file.name.endsWith(".json")) {
        setError("Please drop a valid .json report file (e.g. report.json).");
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        if (content) processJsonText(content);
      };
      reader.readAsText(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        if (content) processJsonText(content);
      };
      reader.readAsText(file);
    }
  };

  const handleReset = () => {
    setUploadedReport(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // If a report is currently loaded, display it with findings and clear button
  if (uploadedReport) {
    return (
      <div className="border border-emerald-500/30 dark:border-emerald-500/25 rounded-xl p-6 bg-white dark:bg-[#111722] space-y-6 font-mono text-xs transition-colors shadow-xs">
        {/* Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span className="text-slate-900 dark:text-slate-100 font-bold text-sm font-sans">
              Viewing Custom Uploaded Report: {uploadedReport.library.name} v{uploadedReport.library.version}
            </span>
            <span className="text-slate-500 text-[11px]">({uploadedReport.runId})</span>
          </div>
          <button
            onClick={handleReset}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition text-xs self-start sm:self-auto shadow-xs font-medium"
          >
            <X className="w-3.5 h-3.5" />
            <span>Close & Return</span>
          </button>
        </div>

        {/* Verification Funnel */}
        <div className="space-y-2">
          <span className="text-[11px] text-slate-500 uppercase tracking-wider block font-semibold">
            Survivorship Funnel
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
            <div className="p-3 rounded-lg border border-blue-200/80 dark:border-slate-800 bg-blue-50/50 dark:bg-slate-950/70">
              <span className="text-[10px] text-blue-800 dark:text-slate-500 uppercase block font-semibold">Candidates</span>
              <span className="text-lg font-bold text-slate-900 dark:text-slate-100">{uploadedReport.funnel.candidates}</span>
            </div>
            <div className="p-3 rounded-lg border border-emerald-500/30 dark:border-emerald-500/20 bg-emerald-50/70 dark:bg-emerald-500/5">
              <span className="text-[10px] text-emerald-800 dark:text-emerald-400 uppercase block font-semibold">Human Validated</span>
              <span className="text-lg font-bold text-emerald-700 dark:text-emerald-400">{uploadedReport.funnel.humanValidated}</span>
            </div>
            <div className="p-3 rounded-lg border border-violet-200/80 dark:border-slate-700 bg-violet-50/50 dark:bg-slate-800/60">
              <span className="text-[10px] text-violet-800 dark:text-slate-300 uppercase block font-semibold">AI-Reviewed</span>
              <span className="text-lg font-bold text-slate-900 dark:text-slate-100">{uploadedReport.funnel.aiReviewed}</span>
            </div>
            <div className="p-3 rounded-lg border border-amber-200/80 dark:border-slate-800 bg-amber-50/50 dark:bg-slate-950/70">
              <span className="text-[10px] text-amber-800 dark:text-slate-400 uppercase block font-semibold">Unresolved</span>
              <span className="text-lg font-bold text-amber-800 dark:text-slate-300">{uploadedReport.funnel.unresolved}</span>
            </div>
            <div className="p-3 rounded-lg border border-rose-200/80 dark:border-slate-800 bg-rose-50/50 dark:bg-slate-950/70">
              <span className="text-[10px] text-rose-800 dark:text-slate-500 uppercase block font-semibold line-through">Rejected</span>
              <span className="text-lg font-bold text-rose-700 dark:text-slate-500">{uploadedReport.funnel.rejected}</span>
            </div>
          </div>
        </div>

        {/* Cost Bar */}
        <CostBar
          confirmedUsd={uploadedReport.cost.confirmedUsd}
          pendingUsd={uploadedReport.cost.pendingUsd}
          byModel={uploadedReport.cost.byModel}
        />

        {/* Findings */}
        <div className="space-y-4 pt-2">
          <span className="text-xs uppercase tracking-wider text-slate-700 dark:text-slate-300 font-semibold block">
            Uploaded Findings ({uploadedReport.findings.length})
          </span>
          <div className="space-y-6">
            {uploadedReport.findings.map((f) => (
              <FindingCard
                key={f.id}
                finding={f}
                runId={uploadedReport.runId}
                runRejectedCost={uploadedReport.cost.rejectedCandidatesCost}
                isDetailed={true}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Dropzone empty state
  return (
    <div className="space-y-2">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-2.5 ${
          isDragging
            ? "border-sky-500 bg-sky-50/70 dark:bg-sky-500/10 text-sky-700 dark:text-sky-300"
            : "border-slate-300/80 hover:border-sky-400 dark:border-slate-800 dark:hover:border-slate-700 bg-gradient-to-b from-white to-slate-50/70 hover:to-sky-50/30 dark:bg-none dark:bg-[#111722]/50 text-slate-600 dark:text-slate-400 shadow-xs"
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".json"
          className="hidden"
        />

        <div className="w-11 h-11 rounded-full border border-sky-200/80 dark:border-slate-800 bg-sky-50 dark:bg-slate-900 flex items-center justify-center text-sky-600 dark:text-sky-400 shadow-2xs">
          <UploadCloud className="w-5 h-5 text-sky-600 dark:text-sky-400" />
        </div>

        <div className="space-y-1">
          <div className="font-mono text-xs text-slate-800 dark:text-slate-200">
            <span className="font-bold text-slate-900 dark:text-slate-100 hover:underline">
              Drop your custom report.json here
            </span>{" "}
            or click to browse
          </div>
          <p className="text-[11px] text-slate-500 font-sans">
            Instantly validates against Schema v1 and visualizes finding cards, 5-question answers, and cost accounting 100% in your browser.
          </p>
        </div>
      </div>

      {error && (
        <div className="border border-rose-300 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/10 rounded-lg p-3.5 text-xs font-mono text-rose-800 dark:text-rose-300 flex items-start gap-2 shadow-xs">
          <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
          <pre className="whitespace-pre-wrap leading-relaxed">{error}</pre>
        </div>
      )}
    </div>
  );
}
