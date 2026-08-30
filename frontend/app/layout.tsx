import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en">
      <body>
        <div className="flex min-h-screen flex-col">
          <header className="border-b border-gray-200 bg-white">
            <div className="mx-auto max-w-3xl px-4 py-4">
              <h1 className="text-xl font-bold text-groww-dark">
                Groww Mutual Fund FAQ Assistant
              </h1>
              <p className="text-sm text-gray-500">
                Facts-only mutual fund information. No investment advice.
              </p>
            </div>
          </header>

          <div className="bg-amber-50 border-b border-amber-200">
            <p className="mx-auto max-w-3xl px-4 py-2 text-xs text-amber-900">
              ⚠ Do not enter PAN, Aadhaar, OTPs, bank details, folio numbers,
              phone numbers, or other personal/account information.
            </p>
          </div>

          <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
            {children}
          </main>

          <footer className="border-t border-gray-200 bg-white">
            <p className="mx-auto max-w-3xl px-4 py-3 text-[11px] leading-snug text-gray-400">
              {DISCLAIMER}
            </p>
          </footer>
        </div>
      </body>
    </html>
  );
}
