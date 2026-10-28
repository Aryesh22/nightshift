import React from "react";
import { FindingStatus } from "@/lib/report/schema";
import { getStatusStyle } from "@/lib/report/format";
import { 
  Check, 
  ShieldCheck, 
  Sparkles, 
  AlertCircle, 
  HelpCircle, 
  X, 
  AlertTriangle 
} from "lucide-react";

interface StatusBadgeProps {
  status: FindingStatus;
  size?: "sm" | "md";
  showIcon?: boolean;
}

export function StatusBadge({ status, size = "md", showIcon = true }: StatusBadgeProps) {
  const style = getStatusStyle(status);

  const renderIcon = () => {
    const iconClass = size === "sm" ? "w-3 h-3 shrink-0" : "w-3.5 h-3.5 shrink-0";
    switch (status) {
      case "maintainer_confirmed":
        return <ShieldCheck className={iconClass} />;
      case "human_validated":
        return <Check className={iconClass} />;
      case "ai_reviewed":
        return <Sparkles className={iconClass} />;
      case "reproducible":
        return <AlertCircle className={iconClass} />;
      case "raw_anomaly":
        return <AlertTriangle className={iconClass} />;
      case "unresolved":
        return <HelpCircle className={iconClass} />;
      case "rejected":
        return <X className={iconClass} />;
      default:
        return null;
    }
  };

  const textSizes = size === "sm" ? "text-[10px] px-2 py-0.5" : "text-xs px-2.5 py-1";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded font-mono font-medium border ${style.badgeBg} ${textSizes}`}
    >
      {showIcon && renderIcon()}
      <span>{style.label}</span>
    </span>
  );
}

