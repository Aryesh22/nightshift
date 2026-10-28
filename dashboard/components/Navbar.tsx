"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";
import { Gauge } from "lucide-react";

interface NavbarProps {
  breadcrumbs?: { label: string; href?: string }[];
}

export function Navbar({ breadcrumbs }: NavbarProps) {
  const pathname = usePathname();

  return (
    <header className="border-b border-slate-200 dark:border-slate-800/80 bg-white/85 dark:bg-[#0b0f17]/85 backdrop-blur-md sticky top-0 z-50 transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Brand & Breadcrumbs */}
        <div className="flex items-center space-x-2.5 text-xs font-mono">
          <Link
            href="/"
            className="font-bold tracking-tight text-slate-900 dark:text-slate-100 hover:text-sky-600 dark:hover:text-sky-400 transition flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]"></span>
            <span>nightshift</span>
          </Link>
          <span className="text-slate-300 dark:text-slate-700">/</span>

          {breadcrumbs && breadcrumbs.length > 0 ? (
            breadcrumbs.map((bc, idx) => (
              <React.Fragment key={idx}>
                {bc.href ? (
                  <Link
                    href={bc.href}
                    className="text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition"
                  >
                    {bc.label}
                  </Link>
                ) : (
                  <span className="px-2 py-0.5 rounded-md bg-slate-100/90 dark:bg-slate-800/80 text-slate-800 dark:text-slate-200 font-medium border border-slate-200/80 dark:border-slate-700">
                    {bc.label}
                  </span>
                )}
                {idx < breadcrumbs.length - 1 && (
                  <span className="text-slate-300 dark:text-slate-700">/</span>
                )}
              </React.Fragment>
            ))
          ) : (
            <span className="text-slate-500 dark:text-slate-400">
              evidence-dashboard
            </span>
          )}
        </div>

        {/* Right side: Nav links + Theme Toggle */}
        <div className="flex items-center space-x-6 text-xs font-mono">
          <nav className="flex items-center space-x-5">
            <Link
              href="/"
              className={`transition ${
                pathname === "/"
                  ? "text-slate-900 dark:text-slate-100 font-semibold underline underline-offset-4 decoration-sky-500"
                  : "text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              runs
            </Link>
            <Link
              href="/benchmark"
              className={`flex items-center gap-1.5 transition ${
                pathname.startsWith("/benchmark")
                  ? "text-slate-900 dark:text-slate-100 font-semibold underline underline-offset-4 decoration-sky-500"
                  : "text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              <Gauge className="w-3.5 h-3.5 text-sky-500" />
              benchmark
            </Link>
          </nav>

          <div className="border-l border-slate-200 dark:border-slate-800 pl-4 flex items-center">
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
