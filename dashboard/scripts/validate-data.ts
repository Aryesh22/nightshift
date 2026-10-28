import fs from "fs";
import path from "path";
import { ReportSchema } from "../lib/report/schema";

const DATA_DIR = path.join(process.cwd(), "data");
const RUNS_DIR = path.join(DATA_DIR, "runs");

const SECRET_PATTERNS = [
  /tvly-[a-zA-Z0-9_-]{20,}/,
  /Bearer\s+[a-zA-Z0-9_\-\.]{20,}/,
  /sk-[a-zA-Z0-9]{20,}/,
  /ghp_[a-zA-Z0-9]{20,}/,
];

const LOCAL_PATH_PATTERNS = [
  /\/home\/[a-zA-Z0-9_-]+\//,
  /\/Users\/[a-zA-Z0-9_-]+\//,
  /[A-Z]:\\[Uu]sers\\[a-zA-Z0-9_-]+\\/,
];

function scanForLeaks(filePath: string, content: string): boolean {
  let hasLeak = false;

  for (const pat of SECRET_PATTERNS) {
    if (pat.test(content)) {
      console.error(`🚨 Security Alert: Potential secret found in ${filePath} matching ${pat}`);
      hasLeak = true;
    }
  }

  for (const pat of LOCAL_PATH_PATTERNS) {
    if (pat.test(content)) {
      console.warn(`⚠️ Warning: Absolute local file path found in ${filePath} matching ${pat}`);
    }
  }

  return !hasLeak;
}

function validateAllData() {
  console.log("🔍 Validating all dataset files in:", DATA_DIR);

  if (!fs.existsSync(RUNS_DIR)) {
    console.log("No runs directory found, skipping run validation.");
    return;
  }

  const entries = fs.readdirSync(RUNS_DIR, { withFileTypes: true });
  const runDirs = entries.filter((e) => e.isDirectory()).map((e) => e.name);

  let errors = 0;

  for (const runId of runDirs) {
    const reportPath = path.join(RUNS_DIR, runId, "report.json");
    if (!fs.existsSync(reportPath)) {
      console.warn(`⚠️ Warning: Folder ${runId} has no report.json`);
      continue;
    }

    const rawContent = fs.readFileSync(reportPath, "utf-8");
    if (!scanForLeaks(reportPath, rawContent)) {
      errors++;
    }

    try {
      const parsedJson = JSON.parse(rawContent);
      const result = ReportSchema.safeParse(parsedJson);

      if (!result.success) {
        console.error(`❌ Schema validation failed for ${reportPath}:`);
        console.error(JSON.stringify(result.error.format(), null, 2));
        errors++;
      } else {
        console.log(`✅ Validated ${runId} (findings: ${result.data.findings.length})`);
      }
    } catch (err) {
      console.error(`❌ JSON parse failed for ${reportPath}:`, err);
      errors++;
    }
  }

  if (errors > 0) {
    console.error(`\n❌ Data validation failed with ${errors} error(s).`);
    process.exit(1);
  } else {
    console.log("\n🎉 All dataset files passed schema and hygiene validation successfully!");
  }
}

validateAllData();

