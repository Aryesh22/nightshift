"use client";

import React, { useState } from "react";
import { Check, Copy } from "lucide-react";

interface CodeBlockProps {
  code: string;
  language?: string;
  title?: string;
  showLineNumbers?: boolean;
}

export function CodeBlock({
  code,
  language = "python",
  title,
  showLineNumbers = false,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy code:", err);
    }
  };

  const lines = code.trim().split("\n");

  return (
    <div className="border border-slate-200 dark:border-slate-800/80 rounded-xl overflow-hidden bg-slate-50/70 dark:bg-[#0b0f17]/70 font-mono text-xs transition-colors shadow-2xs">
      {title && (
        <div className="border-b border-slate-200 dark:border-slate-800/80 px-3.5 py-2.5 bg-slate-100/70 dark:bg-slate-900/40 flex items-center justify-between text-slate-600 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <span className="text-slate-800 dark:text-slate-200 font-medium">{title}</span>
            <span className="text-[10px] text-slate-400 dark:text-slate-500 uppercase">{language}</span>
          </div>
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
                <span>copy</span>
              </>
            )}
          </button>
        </div>
      )}

      <div className="relative overflow-x-auto p-3.5 text-slate-800 dark:text-slate-200">
        {!title && (
          <button
            onClick={handleCopy}
            className="absolute top-2.5 right-2.5 inline-flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-2 py-1 rounded-md shadow-xs"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                <span className="text-emerald-600 dark:text-emerald-400">copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>copy</span>
              </>
            )}
          </button>
        )}

        <pre className="leading-relaxed">
          {lines.map((line, idx) => (
            <div key={idx} className="flex">
              {showLineNumbers && (
                <span className="w-8 shrink-0 text-slate-400 dark:text-slate-600 select-none text-right pr-3 font-mono">
                  {idx + 1}
                </span>
              )}
              <span className="whitespace-pre">{line || " "}</span>
            </div>
          ))}
        </pre>
      </div>
    </div>
  );
}
