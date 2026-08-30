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
                  <ThemeToggle />
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
