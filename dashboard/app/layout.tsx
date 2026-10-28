import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nightshift — Property Testing & Detective Triage",
  description: "Evidence-driven property-based testing and triage reports",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full dark antialiased" suppressHydrationWarning>
      <body className="min-h-full flex flex-col font-sans bg-[#f1f5f9] dark:bg-[#0b0f17] text-slate-900 dark:text-slate-100 selection:bg-sky-500/20 selection:text-sky-900 dark:selection:bg-sky-500/30 dark:selection:text-sky-200 transition-colors duration-150">
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var theme = localStorage.getItem('nightshift-theme');
                if (theme === 'light') {
                  document.documentElement.classList.remove('dark');
                } else {
                  document.documentElement.classList.add('dark');
                }
              } catch (e) {}
            `,
          }}
        />
        {children}
      </body>
    </html>
  );
}
