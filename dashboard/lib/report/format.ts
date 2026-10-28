import { FindingStatus } from "./schema";

export function formatMoney(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) {
    return "n/a";
  }
  if (amount === 0) {
    return "$0.00";
  }
  if (amount < 0.01) {
    return `$${amount.toFixed(4)}`;
  }
  return `$${amount.toFixed(2)}`;
}

export function formatCredits(credits: number | null | undefined): string {
  if (credits === null || credits === undefined || Number.isNaN(credits)) {
    return "0";
  }
  return Number.isInteger(credits) ? credits.toString() : credits.toFixed(1);
}

export function formatDuration(minutes: number | null | undefined): string {
  if (!minutes) return "0 min";
  if (minutes < 1) {
    return `${Math.round(minutes * 60)} sec`;
  }
  return `${minutes.toFixed(1)} min`;
}

export function formatHash(hash: string | null | undefined, length: number = 8): string {
  if (!hash) return "";
  const cleaned = hash.startsWith("sha256:") ? hash.slice(7) : hash;
  return cleaned.slice(0, length);
}

export function getStatusLabel(status: FindingStatus): string {
  switch (status) {
    case "raw_anomaly":
      return "Raw anomaly";
    case "reproducible":
      return "Reproducible";
    case "ai_reviewed":
      return "AI-reviewed candidate";
    case "human_validated":
      return "Human validated";
    case "maintainer_confirmed":
      return "Maintainer confirmed";
    case "unresolved":
      return "Unresolved";
    case "rejected":
      return "Rejected";
    default:
      return status;
  }
}

export interface StatusStyle {
  label: string;
  badgeBg: string;
  badgeText: string;
  borderColor: string;
  dotColor: string;
  iconName: "alert" | "check" | "help" | "x" | "shield" | "sparkles";
}

export function getStatusStyle(status: FindingStatus): StatusStyle {
  switch (status) {
    case "maintainer_confirmed":
      return {
        label: "Maintainer confirmed",
        badgeBg: "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/25",
        badgeText: "text-emerald-800 dark:text-emerald-300",
        borderColor: "border-emerald-200 dark:border-emerald-500/25",
        dotColor: "bg-emerald-500",
        iconName: "shield",
      };
    case "human_validated":
      return {
        label: "Human validated",
        badgeBg: "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/25",
        badgeText: "text-emerald-800 dark:text-emerald-300",
        borderColor: "border-emerald-200 dark:border-emerald-500/25",
        dotColor: "bg-emerald-500",
        iconName: "check",
      };
    case "ai_reviewed":
      return {
        label: "AI-reviewed candidate",
        badgeBg: "bg-slate-100 dark:bg-slate-800/80 text-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-700/80",
        badgeText: "text-slate-800 dark:text-slate-200",
        borderColor: "border-slate-200 dark:border-slate-700/80",
        dotColor: "bg-slate-500",
        iconName: "sparkles",
      };
    case "reproducible":
      return {
        label: "Reproducible",
        badgeBg: "bg-sky-50 dark:bg-sky-500/10 text-sky-800 dark:text-sky-300 border-sky-200 dark:border-sky-500/25",
        badgeText: "text-sky-800 dark:text-sky-300",
        borderColor: "border-sky-200 dark:border-sky-500/25",
        dotColor: "bg-sky-500",
        iconName: "alert",
      };
    case "raw_anomaly":
      return {
        label: "Raw anomaly",
        badgeBg: "bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-500/25",
        badgeText: "text-amber-800 dark:text-amber-300",
        borderColor: "border-amber-200 dark:border-amber-500/25",
        dotColor: "bg-amber-500",
        iconName: "alert",
      };
    case "unresolved":
      return {
        label: "Unresolved",
        badgeBg: "bg-slate-100 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700/60",
        badgeText: "text-slate-600 dark:text-slate-400",
        borderColor: "border-slate-200 dark:border-slate-700/60",
        dotColor: "bg-slate-400",
        iconName: "help",
      };
    case "rejected":
      return {
        label: "Rejected",
        badgeBg: "bg-slate-100 dark:bg-slate-900/60 text-slate-400 dark:text-slate-500 border-slate-200 dark:border-slate-800 line-through",
        badgeText: "text-slate-400 dark:text-slate-500",
        borderColor: "border-slate-200 dark:border-slate-800",
        dotColor: "bg-slate-400",
        iconName: "x",
      };
  }
}

export function formatOutcomeLabel(outcome: string | undefined): {
  label: string;
  isNeutral: boolean;
  isDisproven: boolean;
} {
  switch (outcome) {
    case "no_match_found":
      return {
        label: "No matching issue found by search",
        isNeutral: true,
        isDisproven: false,
      };
    case "exact_existing_issue":
      return {
        label: "Matches existing reported issue",
        isNeutral: false,
        isDisproven: true,
      };
    case "documented_intended":
      return {
        label: "Documented intended behavior",
        isNeutral: false,
        isDisproven: true,
      };
    case "related_issue":
      return {
        label: "Related existing issue or discussion",
        isNeutral: false,
        isDisproven: false,
      };
    case "lookup_unavailable":
      return {
        label: "Search lookup unavailable",
        isNeutral: true,
        isDisproven: false,
      };
    default:
      return {
        label: outcome || "Unknown",
        isNeutral: true,
        isDisproven: false,
      };
  }
}
