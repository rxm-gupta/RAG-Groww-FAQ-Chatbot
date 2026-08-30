import type { ChatResponse } from "@/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Client-side PII pre-check — backend validation remains authoritative. */
const CLIENT_PII_PATTERNS: RegExp[] = [
  /\b[A-Z]{5}[0-9]{4}[A-Z]\b/, // PAN
  /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/, // Aadhaar-like
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/, // email
  /\b(?:\+?91[\s-]?)?[6-9]\d{9}\b/, // phone
  /\botp\b/i,
];

export function containsObviousPii(text: string): boolean {
  return CLIENT_PII_PATTERNS.some((re) => re.test(text));
}

export async function askQuestion(
  question: string,
  sessionId: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "Sorry, I couldn't process that right now.");
  }
  return res.json();
}
