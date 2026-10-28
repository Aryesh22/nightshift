import { Finding, FindingStatus, Report } from "./schema";
import {
  formatCredits,
  formatHash,
  formatMoney,
  formatOutcomeLabel,
  getStatusStyle,
  StatusStyle,
} from "./format";

export interface NormalizedEvidence {
  source: string;
  excerpt: string;
  retrieved: string;
  isPinnedCommit: boolean;
  contentHash: string;
}

export interface NormalizedCheck {
  question: string;
  tool: string;
  result: string;
  effect: "supports" | "refutes" | "neutral" | string;
  effectColor: string;
}

export interface NormalizedKnownBehaviour {
  outcome: string;
  label: string;
  links: string[];
  note: string;
  isUncertain: boolean;
}

export interface NormalizedFinding {
  id: string;
  title: string;
  status: FindingStatus;
  statusStyle: StatusStyle;
  contract: {
    id: string;
    version: number;
    family: string;
    claim: string;
    status: string;
    hash: string;
    shortHash: string;
    evidence: NormalizedEvidence[];
    adapterApproval: string | null;
    wrapperHash: string | null;
  };
  repro: string;
  actual: string;
  expected: string;
  control: string;
  traceback: string;
  replays: {
    passed: number;
    attempted: number;
    rate: string;
    allPassed: boolean;
  };
  checks: NormalizedCheck[];
  knownBehaviour: NormalizedKnownBehaviour | null;
  uncertainty: string;
  rejectionReason: string | null;
  rootCause: string | null;
  patch: {
    diff: string | null;
    validation: string | null;
    hasPatch: boolean;
  };
  cost: {
    usd: number;
    formatted: string;
  };
  routeTrace: {
    stage: string;
    model: string;
    thinking: number | null;
    costUsd: number;
    cached: boolean;
    escalationReason: string | null;
  }[];
  hasUltra: boolean;
}

export interface NormalizedReport {
  runId: string;
  library: {
    name: string;
    version: string;
    repo: string | null;
  };
  mode: "core" | "baseline";
  airgapped: boolean;
  isSample: boolean;
  createdAt: string;
  commitRef: string | null;
  stats: {
    contracts: number;
    campaigns: number;
    infraFailures: number;
    humanReviewMinutes: number;
    assertionsRun: number | null;
    testBodiesRun: number | null;
    shrinkReplaysRun: number | null;
  };
  statusCounts: Record<FindingStatus, number>;
  funnel: {
    candidates: number;
    reproducible: number;
    aiReviewed: number;
    humanValidated: number;
    maintainerConfirmed: number;
    unresolved: number;
    rejected: number;
  };
  cost: {
    confirmedUsd: number;
    pendingUsd: number;
    totalEstimatedUsd: number;
    byModel: Record<string, number>;
    costPerAiReviewed: number | null;
    costPerHumanValidated: number | null;
    rejectedCandidatesCost: number;
  };
  tavily: {
    creditsUsed: number;
    creditsPending: number;
    hasTavily: boolean;
  };
  findings: NormalizedFinding[];
  activeFindings: NormalizedFinding[];
  rejectedFindings: NormalizedFinding[];
  unresolvedFindings: NormalizedFinding[];
}

function checkEffectColor(effect: string): string {
  switch (effect.toLowerCase()) {
    case "supports":
      return "text-emerald-400 bg-emerald-950/60 border-emerald-500/30";
    case "refutes":
      return "text-rose-400 bg-rose-950/60 border-rose-500/30";
    default:
      return "text-slate-400 bg-slate-900 border-slate-700";
  }
}

export function normalizeFinding(raw: Finding): NormalizedFinding {
  const c = raw.contract;
  const status = raw.status;
  const style = getStatusStyle(status);

  const evidence: NormalizedEvidence[] = (c.evidence || []).map((e) => ({
    source: e.source,
    excerpt: e.excerpt,
    retrieved: e.retrieved || "manual",
    contentHash: e.content_hash || "",
    isPinnedCommit:
      e.source.includes("/commit/") ||
      e.source.includes("/tree/") ||
      e.source.includes("/blob/"),
  }));

  const checks: NormalizedCheck[] = (raw.checks || []).map((ck) => ({
    question: ck.question,
    tool: ck.tool,
    result: ck.result,
    effect: ck.effect,
    effectColor: checkEffectColor(ck.effect),
  }));

  let knownBehaviour: NormalizedKnownBehaviour | null = null;
  if (raw.known_behaviour) {
    const formatted = formatOutcomeLabel(raw.known_behaviour.outcome);
    knownBehaviour = {
      outcome: raw.known_behaviour.outcome,
      label: formatted.label,
      links: raw.known_behaviour.links || [],
      note: raw.known_behaviour.note || "",
      isUncertain: !formatted.isDisproven,
    };
  }

  const replaysPassed = raw.replays_passed ?? 0;
  const replaysAttempted = raw.replays_attempted ?? 0;
  const replaysRate =
    replaysAttempted > 0
      ? `${replaysPassed}/${replaysAttempted}`
      : "0/0";

  const hasUltra = (raw.route_trace || []).some(
    (s) => s.model.toLowerCase() === "ultra" || s.stage === "review"
  );

  return {
    id: raw.id,
    title: raw.title,
    status,
    statusStyle: style,
    contract: {
      id: c.contract_id,
      version: c.version ?? 1,
      family: c.family || "roundtrip",
      claim: c.claim,
      status: c.status || "explicit",
      hash: c.hash || "",
      shortHash: formatHash(c.hash),
      evidence,
      adapterApproval: c.adapter_approval ?? null,
      wrapperHash: c.wrapper_hash ?? null,
    },
    repro: raw.repro,
    actual: raw.actual || "",
    expected: raw.expected || c.claim,
    control: raw.control || "",
    traceback: raw.traceback || "",
    replays: {
      passed: replaysPassed,
      attempted: replaysAttempted,
      rate: replaysRate,
      allPassed: replaysAttempted > 0 && replaysPassed === replaysAttempted,
    },
    checks,
    knownBehaviour,
    uncertainty: raw.uncertainty || "",
    rejectionReason: raw.rejection_reason || null,
    rootCause: raw.root_cause || null,
    patch: {
      diff: raw.patch_diff || null,
      validation: raw.patch_validation || null,
      hasPatch: Boolean(raw.patch_diff),
    },
    cost: {
      usd: raw.cost_usd ?? 0,
      formatted: formatMoney(raw.cost_usd ?? 0),
    },
    routeTrace: (raw.route_trace || []).map((s) => ({
      stage: s.stage,
      model: s.model,
      thinking: s.thinking ?? null,
      costUsd: s.cost_usd ?? 0,
      cached: Boolean(s.cached),
      escalationReason: s.escalation_reason ?? null,
    })),
    hasUltra,
  };
}

export function normalizeReport(raw: Report): NormalizedReport {
  const findings = (raw.findings || []).map(normalizeFinding);

  const statusCounts: Record<FindingStatus, number> = {
    raw_anomaly: 0,
    reproducible: 0,
    ai_reviewed: 0,
    human_validated: 0,
    maintainer_confirmed: 0,
    unresolved: 0,
    rejected: 0,
  };

  findings.forEach((f) => {
    statusCounts[f.status] = (statusCounts[f.status] || 0) + 1;
  });

  const activeFindings = findings.filter(
    (f) => f.status !== "rejected" && f.status !== "unresolved"
  );
  const rejectedFindings = findings.filter((f) => f.status === "rejected");
  const unresolvedFindings = findings.filter((f) => f.status === "unresolved");

  const totalConfirmedSpend = raw.stats.cost_usd ?? 0;
  const pendingSpend =
    raw.accounting?.pending_usd ?? raw.stats.pending_cost_usd ?? 0;
  const totalEstimatedUsd = totalConfirmedSpend + pendingSpend;

  const rejectedCandidatesCost = rejectedFindings.reduce(
    (acc, f) => acc + f.cost.usd,
    0
  );

  const aiReviewedCount =
    statusCounts.ai_reviewed +
    statusCounts.human_validated +
    statusCounts.maintainer_confirmed;
  const humanValidatedCount =
    statusCounts.human_validated + statusCounts.maintainer_confirmed;

  const costPerAiReviewed =
    aiReviewedCount > 0 ? totalConfirmedSpend / aiReviewedCount : null;
  const costPerHumanValidated =
    humanValidatedCount > 0 ? totalConfirmedSpend / humanValidatedCount : null;

  const tavilyUsed =
    raw.tavily_ledger?.credits_used ?? raw.stats.tavily_credits ?? 0;
  const tavilyPending =
    raw.tavily_ledger?.credits_pending ?? raw.stats.pending_tavily_credits ?? 0;

  return {
    runId: raw.run_id,
    library: {
      name: raw.library.name,
      version: raw.library.version,
      repo: raw.library.repo ?? null,
    },
    mode: raw.mode || "core",
    airgapped: Boolean(raw.airgapped),
    isSample: Boolean(raw.is_sample || raw.run_id.startsWith("FAKE-")),
    createdAt: raw.created_at || "Recent run",
    commitRef: raw.commit_ref ?? null,
    stats: {
      contracts: raw.stats.contracts ?? 0,
      campaigns: raw.stats.campaigns ?? 0,
      infraFailures: raw.stats.infra_failures ?? 0,
      humanReviewMinutes: raw.stats.human_review_minutes ?? 0,
      assertionsRun: raw.stats.assertions_run ?? null,
      testBodiesRun: raw.stats.test_bodies_run ?? null,
      shrinkReplaysRun: raw.stats.shrink_replays_run ?? null,
    },
    statusCounts,
    funnel: {
      candidates: findings.length,
      reproducible:
        statusCounts.reproducible +
        statusCounts.ai_reviewed +
        statusCounts.human_validated +
        statusCounts.maintainer_confirmed,
      aiReviewed: statusCounts.ai_reviewed,
      humanValidated: statusCounts.human_validated,
      maintainerConfirmed: statusCounts.maintainer_confirmed,
      unresolved: statusCounts.unresolved,
      rejected: statusCounts.rejected,
    },
    cost: {
      confirmedUsd: totalConfirmedSpend,
      pendingUsd: pendingSpend,
      totalEstimatedUsd,
      byModel: raw.cost_by_model || {},
      costPerAiReviewed,
      costPerHumanValidated,
      rejectedCandidatesCost,
    },
    tavily: {
      creditsUsed: tavilyUsed,
      creditsPending: tavilyPending,
      hasTavily: tavilyUsed > 0 || tavilyPending > 0,
    },
    findings,
    activeFindings,
    rejectedFindings,
    unresolvedFindings,
  };
}

