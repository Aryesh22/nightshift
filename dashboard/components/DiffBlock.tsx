"use client";

import React, { useState } from "react";
import { Check, Copy } from "lucide-react";

interface DiffBlockProps {
  diff: string;
  title?: string;
}

export function DiffBlock({ diff, title = "Proposed Patch" }: DiffBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(diff);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy diff:", err);
    }
  };

  const lines = diff.trim().split("\n");

  return (
    <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl overflow-hidden bg-slate-50/70 dark:bg-[#0b0f17]/70 font-mono text-xs transition-colors shadow-2xs">
      <div className="border-b border-slate-200 dark:border-slate-800/80 px-3.5 py-2.5 bg-slate-100/70 dark:bg-slate-900/40 flex items-center justify-between text-slate-600 dark:text-slate-400">
        <span className="text-slate-800 dark:text-slate-200 font-medium">{title}</span>
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition px-2 py-0.5 rounded-md hover:bg-slate-200/60 dark:hover:bg-slate-800"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
              <span className="text-emerald-600 dark:text-emerald-400">copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>copy diff</span>
            </>
          )}
        </button>
      </div>

      <div className="overflow-x-auto p-3.5 text-slate-800 dark:text-slate-200">
        <pre className="leading-relaxed">
          {lines.map((line, idx) => {
            let lineClass = "text-slate-600 dark:text-slate-400";
            if (line.startsWith("+") && !line.startsWith("+++")) {
              lineClass = "text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-1 rounded-sm";
            } else if (line.startsWith("-") && !line.startsWith("---")) {
              lineClass = "text-rose-700 dark:text-rose-400 bg-rose-500/10 px-1 rounded-sm";
            } else if (line.startsWith("@@")) {
              lineClass = "text-sky-700 dark:text-sky-400/80 font-semibold";
            }

            return (
              <div key={idx} className={`${lineClass} whitespace-pre`}>
                {line || " "}
              </div>
            );
          })}
        </pre>
      </div>
    </div>
  );
}
