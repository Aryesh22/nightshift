import fs from "fs";
import path from "path";
import { ReportSchema, Report } from "../lib/report/schema";
import { normalizeReport } from "../lib/report/normalize";

const DATA_DIR = path.join(process.cwd(), "data");
const RUNS_DIR = path.join(DATA_DIR, "runs");
const INDEX_FILE = path.join(RUNS_DIR, "index.json");

// Regular expressions for sensitive data scrubbing
const SECRET_REGEX = /(?:tvly-[a-zA-Z0-9_-]{16,}|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9_\-\.]{20,})/gi;
const PATH_REGEX_WIN = /[A-Z]:\\[Uu]sers\\[a-zA-Z0-9_-]+\\[^\s"'\\]+/gi;
const PATH_REGEX_UNIX = /\/(?:home|Users)\/[a-zA-Z0-9_-]+\/[^\s"']+/gi;
const NEBIUS_HOST_REGEX = /(?:ssh:\/\/|https?:\/\/)?(?:[a-zA-Z0-9_-]+@)?(?:nebius-[a-zA-Z0-9_-]+|\b(?:10|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b)/gi;

function scrubString(text: string): string {
  return text
    .replace(SECRET_REGEX, "[REDACTED_SECRET]")
    .replace(PATH_REGEX_WIN, "[REDACTED_LOCAL_PATH]")
    .replace(PATH_REGEX_UNIX, "[REDACTED_LOCAL_PATH]")
    .replace(NEBIUS_HOST_REGEX, "[REDACTED_HOST]");
}

function deepScrub(obj: any): any {
  if (typeof obj === "string") {
    return scrubString(obj);
  }
  if (Array.isArray(obj)) {
    return obj.map(deepScrub);
  }
  if (obj !== null && typeof obj === "object") {
    const res: Record<string, any> = {};
    for (const [k, v] of Object.entries(obj)) {
      res[k] = deepScrub(v);
    }
    return res;
  }
  return obj;
}

function updateIndexJson(normalizedReport: ReturnType<typeof normalizeReport>) {
  let index: any[] = [];
  if (fs.existsSync(INDEX_FILE)) {
    try {
      index = JSON.parse(fs.readFileSync(INDEX_FILE, "utf-8"));
    } catch {
      index = [];
    }
  }

  // Remove existing entry for this runId if present
  index = index.filter((item) => item.runId !== normalizedReport.runId);

  // Add new summary entry
  index.unshift({
    runId: normalizedReport.runId,
    libraryName: normalizedReport.library.name,
    version: normalizedReport.library.version,
    mode: normalizedReport.mode,
    createdAt: normalizedReport.createdAt,
    isSample: normalizedReport.isSample,
    totalFindings: normalizedReport.findings.length,
    activeCount: normalizedReport.activeFindings.length,
    humanValidatedCount:
      normalizedReport.statusCounts.human_validated +
      normalizedReport.statusCounts.maintainer_confirmed,
    aiReviewedCount: normalizedReport.statusCounts.ai_reviewed,
    unresolvedCount: normalizedReport.statusCounts.unresolved,
    rejectedCount: normalizedReport.statusCounts.rejected,
    confirmedCostUsd: normalizedReport.cost.confirmedUsd,
    pendingCostUsd: normalizedReport.cost.pendingUsd,
  });

  fs.writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2) + "\n");
}

function syncRun(sourceDir: string, isSample: boolean = false) {
  console.log(`\n🚀 Starting Nightshift Run Sync from: ${sourceDir}`);

  const reportPath = path.join(sourceDir, "report.json");
  if (!fs.existsSync(reportPath)) {
    console.error(`❌ Error: File not found at ${reportPath}`);
    process.exit(1);
  }

  let rawContent: string;
  let parsedJson: any;

  try {
    rawContent = fs.readFileSync(reportPath, "utf-8");
    parsedJson = JSON.parse(rawContent);
  } catch (err: any) {
    console.error(`❌ Failed to read/parse report.json: ${err.message}`);
    process.exit(1);
  }

  // 1. Zod schema validation
  console.log("🔍 Validating schema against Schema v1...");
  const validation = ReportSchema.safeParse(parsedJson);
  if (!validation.success) {
    console.error("❌ Schema validation failed with errors:");
    validation.error.issues.forEach((issue) => {
      console.error(`  - Field "${issue.path.join(".")}": ${issue.message}`);
    });
    process.exit(1);
  }

  const validReport: Report = validation.data;
  if (isSample) {
    validReport.is_sample = true;
  }

  console.log(`✅ Schema validated successfully for run: ${validReport.run_id}`);

  // 2. Deep Sanitization & Scrubbing
  console.log("🧹 Scrubbing credentials, local machine paths, and VM IPs...");
  const scrubbedReport = deepScrub(validReport);

  // 3. Write into dashboard/data/runs/<run_id>/
  const targetDir = path.join(RUNS_DIR, validReport.run_id);
  fs.mkdirSync(targetDir, { recursive: true });

  const targetReportPath = path.join(targetDir, "report.json");
  fs.writeFileSync(targetReportPath, JSON.stringify(scrubbedReport, null, 2) + "\n");
  console.log(`💾 Saved scrubbed report to: ${targetReportPath}`);

  // 4. Copy any supplementary artifacts (logs, receipts, diffs)
  const artifactsSourceDir = path.join(sourceDir, "artifacts");
  if (fs.existsSync(artifactsSourceDir)) {
    const artifactsTargetDir = path.join(targetDir, "artifacts");
    fs.mkdirSync(artifactsTargetDir, { recursive: true });
    const artifactFiles = fs.readdirSync(artifactsSourceDir);
    artifactFiles.forEach((file) => {
      const srcFile = path.join(artifactsSourceDir, file);
      const destFile = path.join(artifactsTargetDir, file);
      const fileContent = fs.readFileSync(srcFile, "utf-8");
      fs.writeFileSync(destFile, scrubString(fileContent));
    });
    console.log(`📁 Scrubbed and copied ${artifactFiles.length} supplementary artifacts`);
  }

  // 5. Update index.json
  const normalized = normalizeReport(scrubbedReport);
  updateIndexJson(normalized);
  console.log(`📋 Updated runs index in: ${INDEX_FILE}`);

  // 6. Summary Output
  console.log("\n================ SYNC SUMMARY ================");
  console.log(`Package:          ${normalized.library.name} v${normalized.library.version}`);
  console.log(`Run ID:           ${normalized.runId}`);
  console.log(`Mode:             ${normalized.mode} (airgapped: ${normalized.airgapped})`);
  console.log(`Candidates:       ${normalized.findings.length}`);
  console.log(`Human Validated:  ${normalized.funnel.humanValidated}`);
  console.log(`AI-Reviewed:      ${normalized.funnel.aiReviewed}`);
  console.log(`Unresolved:       ${normalized.funnel.unresolved}`);
  console.log(`Rejected:         ${normalized.funnel.rejected}`);
  console.log(`Confirmed Cost:   $${normalized.cost.confirmedUsd.toFixed(4)}`);
  console.log(`Pending Cost:     $${normalized.cost.pendingUsd.toFixed(4)}`);
  console.log("==============================================\n");
}

const args = process.argv.slice(2);
if (args.length === 0) {
  console.log("Usage: npx tsx scripts/sync-run.ts <path-to-run-folder> [--is-sample]");
  process.exit(0);
}

const sourceFolder = args[0];
const isSampleFlag = args.includes("--is-sample");
syncRun(sourceFolder, isSampleFlag);

