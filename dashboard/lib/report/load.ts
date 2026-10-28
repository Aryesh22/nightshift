import fs from "fs";
import path from "path";
import { Report, ReportSchema } from "./schema";
import { NormalizedReport, normalizeReport } from "./normalize";

const DATA_DIR = path.join(process.cwd(), "data");
const RUNS_DIR = path.join(DATA_DIR, "runs");
const VALIDATION_DIR = path.join(DATA_DIR, "validation");
const BENCHMARK_DIR = path.join(DATA_DIR, "benchmark");

export interface RunSummary {
  runId: string;
  libraryName: string;
  version: string;
  mode: "core" | "baseline";
  createdAt: string;
  isSample: boolean;
  totalFindings: number;
  activeCount: number;
  humanValidatedCount: number;
  aiReviewedCount: number;
  unresolvedCount: number;
  rejectedCount: number;
  confirmedCostUsd: number;
  pendingCostUsd: number;
}

export function getAllRunIds(): string[] {
  if (!fs.existsSync(RUNS_DIR)) {
    return [];
  }
  const entries = fs.readdirSync(RUNS_DIR, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((id) => fs.existsSync(path.join(RUNS_DIR, id, "report.json")));
}

export function getRawReport(runId: string): Report | null {
  const filePath = path.join(RUNS_DIR, runId, "report.json");
  if (!fs.existsSync(filePath)) {
    return null;
  }
  try {
    const content = fs.readFileSync(filePath, "utf-8");
    const json = JSON.parse(content);

    // Apply human validation overlay if present
    const overlayPath = path.join(VALIDATION_DIR, `${runId}.json`);
    if (fs.existsSync(overlayPath)) {
      try {
        const overlayContent = fs.readFileSync(overlayPath, "utf-8");
        const overlay = JSON.parse(overlayContent);
        if (overlay && Array.isArray(overlay.validations)) {
          const map = new Map<string, { status: string; notes?: string; validator?: string }>();
          overlay.validations.forEach((v: { finding_id: string; status: string; notes?: string; validator?: string }) => {
            map.set(v.finding_id, v);
          });
          if (Array.isArray(json.findings)) {
            json.findings = json.findings.map((f: { id: string; status: string; uncertainty?: string }) => {
              const item = map.get(f.id);
              if (item) {
                return {
                  ...f,
                  status: item.status,
                  uncertainty: item.notes ? `${f.uncertainty || ""} [Validator: ${item.notes}]`.trim() : f.uncertainty,
                };
              }
              return f;
            });
          }
        }
      } catch (err) {
        console.warn(`Failed to merge validation overlay for ${runId}:`, err);
      }
    }

    return ReportSchema.parse(json);
  } catch (err) {
    console.error(`Error loading report ${runId}:`, err);
    return null;
  }
}

export function getNormalizedReport(runId: string): NormalizedReport | null {
  const raw = getRawReport(runId);
  if (!raw) return null;
  return normalizeReport(raw);
}

export function getAllRunSummaries(): RunSummary[] {
  const indexFile = path.join(RUNS_DIR, "index.json");
  if (fs.existsSync(indexFile)) {
    try {
      const content = fs.readFileSync(indexFile, "utf-8");
      return JSON.parse(content);
    } catch {
      // fallback to scanning directories
    }
  }

  const runIds = getAllRunIds();
  const summaries: RunSummary[] = [];

  for (const id of runIds) {
    const report = getNormalizedReport(id);
    if (!report) continue;
    summaries.push({
      runId: report.runId,
      libraryName: report.library.name,
      version: report.library.version,
      mode: report.mode,
      createdAt: report.createdAt,
      isSample: report.isSample,
      totalFindings: report.findings.length,
      activeCount: report.activeFindings.length,
      humanValidatedCount: report.statusCounts.human_validated + report.statusCounts.maintainer_confirmed,
      aiReviewedCount: report.statusCounts.ai_reviewed,
      unresolvedCount: report.statusCounts.unresolved,
      rejectedCount: report.statusCounts.rejected,
      confirmedCostUsd: report.cost.confirmedUsd,
      pendingCostUsd: report.cost.pendingUsd,
    });
  }

  return summaries;
}

export interface BenchmarkTaskResult {
  taskId: string;
  level: "L1" | "L2" | "L3";
  baseline: {
    status: "completed" | "failed" | "timeout" | "not_run";
    evaluatorDetected: boolean | null;
    findingsTotal: number;
    costUsd: number;
    wallSeconds: number;
    failureReason?: string;
  };
  nightshiftCore: {
    status: "completed" | "failed" | "timeout" | "not_run";
    evaluatorDetected: boolean | null;
    findingsTotal: number;
    findingsRejected: number;
    findingsUnresolved: number;
    costUsd: number;
    wallSeconds: number;
    failureReason?: string;
  };
}

export interface BenchmarkData {
  config: {
    commitSha: string;
    totalRuns: number;
    budgetCapTotal: number;
    perRunBudgetCap: number;
    models: {
      lightning: string;
      super: string;
      ultra: string;
    };
    selectionRulesSeed: number;
    frozenDate: string;
    asymmetryNote: string;
  };
  summary: {
    baselineDetectedRatio: string;
    coreDetectedRatio: string;
    baselineTotalCost: number;
    coreTotalCost: number;
    baselineFailures: number;
    coreFailures: number;
    meanTimeBaselineSec: number;
    meanTimeCoreSec: number;
  };
  tasks: BenchmarkTaskResult[];
}

export function getBenchmarkData(): BenchmarkData | null {
  const filePath = path.join(BENCHMARK_DIR, "results.json");
  if (!fs.existsSync(filePath)) {
    return null;
  }
  try {
    const content = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(content);
  } catch (err) {
    console.error("Error loading benchmark results:", err);
    return null;
  }
}

