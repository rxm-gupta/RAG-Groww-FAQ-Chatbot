import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThemeToggle } from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "Groww Mutual Fund FAQ Assistant",
  description: "Facts-only mutual fund information. No investment advice.",
};

const DISCLAIMER =
  "Facts-only assistant. This chatbot provides factual information from official public sources and does not provide investment, financial, portfolio, or tax advice. Do not enter PAN, Aadhaar, OTPs, bank details, folio numbers, or other personal/account information.";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <div className="flex min-h-screen flex-col">
            <header className="border-b border-line bg-surface">
              <div className="mx-auto max-w-3xl px-4 py-4">
                <div className="flex items-center justify-between">
                  <h1 className="text-xl font-bold text-ink">
                    Groww Mutual Fund FAQ Assistant
                  </h1>
                  <div className="flex items-center gap-2">
                    <a
                      href="https://github.com/rxm-gupta/RAG-Groww-FAQ-Chatbot"
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label="View the project repository on GitHub"
                      className="rounded-md p-2 text-slate-600 transition-transform hover:scale-110 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/80 dark:hover:text-white"
                    >
                      <svg
                        className="h-5 w-5"
                        fill="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.167 6.839 9.49.5.092.682-.217.682-.482 0-.237-.009-1.026-.013-1.86-2.782.604-3.369-1.18-3.369-1.18-.455-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.004.07 1.532 1.03 1.532 1.03.892 1.529 2.341 1.087 2.91.831.091-.646.349-1.087.635-1.337-2.22-.253-4.555-1.11-4.555-4.942 0-1.092.39-1.984 1.029-2.683-.103-.253-.446-1.271.098-2.65 0 0 .84-.269 2.75 1.025A9.564 9.564 0 0 1 12 6.356a9.59 9.59 0 0 1 2.504.337c1.909-1.294 2.748-1.025 2.748-1.025.546 1.379.203 2.397.1 2.65.64.699 1.028 1.591 1.028 2.683 0 3.841-2.339 4.686-4.566 4.935.359.31.678.92.678 1.855 0 1.34-.012 2.421-.012 2.751 0 .267.18.578.688.48A10.001 10.001 0 0 0 22 12c0-5.523-4.477-10-10-10Z" />
                      </svg>
                    </a>
                    <ThemeToggle />
                  </div>
                </div>
                <p className="text-sm text-muted">
                  Facts-only mutual fund information. No investment advice.
                </p>
              </div>
            </header>

            <div className="border-b border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10">
              <p className="mx-auto max-w-3xl px-4 py-2 text-xs text-amber-900 dark:text-amber-300">
                ⚠ Do not enter PAN, Aadhaar, OTPs, bank details, folio numbers,
                phone numbers, or other personal/account information.
              </p>
            </div>

            <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
              {children}
            </main>

            <footer className="border-t border-line bg-surface">
              <p className="mx-auto max-w-3xl px-4 py-3 text-[11px] leading-snug text-muted">
                {DISCLAIMER}
              </p>
            </footer>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
