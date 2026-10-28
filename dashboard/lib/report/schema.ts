import { z } from "zod";

export const FindingStatusSchema = z.enum([
  "raw_anomaly",
  "reproducible",
  "ai_reviewed",
  "human_validated",
  "maintainer_confirmed",
  "unresolved",
  "rejected",
]);
export type FindingStatus = z.infer<typeof FindingStatusSchema>;

export const VALIDATED_STATUSES: readonly FindingStatus[] = [
  "human_validated",
  "maintainer_confirmed",
] as const;

export const RouteStepSchema = z.object({
  stage: z.string(), // contract | strategy | investigate | known_behaviour | review | patch
  model: z.string(), // lightning | super | ultra
  thinking: z.number().nullable().optional(),
  cost_usd: z.number().default(0),
  cached: z.boolean().default(false),
  escalation_reason: z.string().nullable().optional(),
});
export type RouteStep = z.infer<typeof RouteStepSchema>;

export const EvidenceRefSchema = z.object({
  source: z.string(),
  excerpt: z.string(),
  retrieved: z.string().default(""),
  content_hash: z.string().default(""),
});
export type EvidenceRef = z.infer<typeof EvidenceRefSchema>;

export const ContractRefSchema = z.object({
  contract_id: z.string(),
  version: z.number().default(1),
  hash: z.string().default(""),
  family: z.string().default("roundtrip"),
  claim: z.string(),
  status: z.string().default("explicit"),
  evidence: z.array(EvidenceRefSchema).default([]),
  adapter_approval: z.string().nullable().optional(),
  wrapper_hash: z.string().nullable().optional(),
});
export type ContractRef = z.infer<typeof ContractRefSchema>;

export const CheckEffectSchema = z.enum(["supports", "refutes", "neutral"]);
export type CheckEffect = z.infer<typeof CheckEffectSchema>;

export const CheckSchema = z.object({
  question: z.string(),
  tool: z.string(),
  result: z.string(),
  effect: z.union([CheckEffectSchema, z.string()]),
});
export type Check = z.infer<typeof CheckSchema>;

export const KnownBehaviourOutcomeSchema = z.enum([
  "exact_existing_issue",
  "documented_intended",
  "related_issue",
  "no_match_found",
  "lookup_unavailable",
]);
export type KnownBehaviourOutcome = z.infer<typeof KnownBehaviourOutcomeSchema>;

export const KnownBehaviourSchema = z.object({
  outcome: z.union([KnownBehaviourOutcomeSchema, z.string()]),
  links: z.array(z.string()).default([]),
  note: z.string().default(""),
});
export type KnownBehaviour = z.infer<typeof KnownBehaviourSchema>;

export const FindingSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: FindingStatusSchema,
  contract: ContractRefSchema,
  repro: z.string(),
  actual: z.string().default(""),
  expected: z.string().default(""),
  traceback: z.string().default(""),
  control: z.string().default(""),
  replays_passed: z.number().default(0),
  replays_attempted: z.number().default(0),
  checks: z.array(CheckSchema).default([]),
  known_behaviour: KnownBehaviourSchema.nullable().optional(),
  uncertainty: z.string().default(""),
  rejection_reason: z.string().nullable().optional(),
  root_cause: z.string().nullable().optional(),
  patch_diff: z.string().nullable().optional(),
  patch_validation: z.string().nullable().optional(),
  cost_usd: z.number().default(0),
  route_trace: z.array(RouteStepSchema).default([]),
}).passthrough();
export type Finding = z.infer<typeof FindingSchema>;

export const LibrarySchema = z.object({
  name: z.string(),
  version: z.string(),
  repo: z.string().nullable().optional(),
});
export type Library = z.infer<typeof LibrarySchema>;

export const StatsSchema = z.object({
  contracts: z.number().default(0),
  campaigns: z.number().default(0),
  infra_failures: z.number().default(0),
  cost_usd: z.number().default(0),
  tavily_credits: z.number().default(0),
  human_review_minutes: z.number().default(0),
  // Core / extended execution manifest fields (all optional for baseline)
  assertions_run: z.number().optional(),
  test_bodies_run: z.number().optional(),
  shrink_replays_run: z.number().optional(),
  pending_cost_usd: z.number().default(0),
  pending_tavily_credits: z.number().default(0),
}).passthrough();
export type Stats = z.infer<typeof StatsSchema>;

export const AccountingItemSchema = z.object({
  name: z.string(),
  amount_usd: z.number().default(0),
  status: z.enum(["confirmed", "pending", "estimated"]).default("confirmed"),
  description: z.string().optional(),
});
export type AccountingItem = z.infer<typeof AccountingItemSchema>;

export const ReportSchema = z.object({
  schema_version: z.literal(1),
  run_id: z.string(),
  library: LibrarySchema,
  stats: StatsSchema,
  cost_by_model: z.record(z.string(), z.number()).default({}),
  findings: z.array(FindingSchema).default([]),
  status_counts: z.record(z.string(), z.number()).optional(),
  cost_per_validated_finding: z.number().nullable().optional(),

  // Optional metadata / Core-only extensions
  mode: z.enum(["core", "baseline"]).default("core").optional(),
  airgapped: z.boolean().default(false).optional(),
  budget_cap_usd: z.number().optional(),
  created_at: z.string().optional(),
  commit_ref: z.string().optional(),
  is_sample: z.boolean().default(false).optional(),
  retrieval_receipts: z.array(z.record(z.string(), z.any())).default([]).optional(),
  retrieval_failures: z.array(z.record(z.string(), z.any())).default([]).optional(),
  contracts: z.array(z.record(z.string(), z.any())).default([]).optional(),
  accounting: z.object({
    confirmed_usd: z.number().optional(),
    pending_usd: z.number().optional(),
    items: z.array(AccountingItemSchema).optional(),
  }).passthrough().optional(),
  tavily_ledger: z.object({
    credits_used: z.number().optional(),
    credits_pending: z.number().optional(),
    receipts_count: z.number().optional(),
  }).passthrough().optional(),
  compatibility_note: z.string().optional(),
}).passthrough();
export type Report = z.infer<typeof ReportSchema>;

export function parseReport(data: unknown): Report {
  return ReportSchema.parse(data);
}

export function safeParseReport(data: unknown) {
  return ReportSchema.safeParse(data);
}

