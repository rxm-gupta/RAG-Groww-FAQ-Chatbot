"use client";

import { useState } from "react";
import { AnswerCard } from "@/components/AnswerCard";
import { askQuestion, containsObviousPii } from "@/lib/api";
import type { ChatResponse } from "@/types";

interface Turn {
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
}

const EXAMPLES = [
  "What is the exit load of HDFC Small Cap Fund?",
  "What is the lock-in period of HDFC ELSS Tax Saver Fund?",
  "What is the riskometer for Flexi Cap Fund?",
];

export default function Home() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState(() => crypto.randomUUID());

  async function ask(question: string) {
    const q = question.trim();
    if (!q || loading) return;

    setError(null);
    setTurns((t) => [...t, { role: "user", text: q }]);
    setInput("");
    setLoading(true);

    if (containsObviousPii(q)) {
      setTurns((t) => [
        ...t,
        {
          role: "assistant",
          text: "Please do not share personal or account information (PAN, Aadhaar, OTPs, bank details, folio numbers). You can ask general factual questions about the HDFC Mutual Fund schemes.",
        },
      ]);
      setLoading(false);
      return;
    }

    try {
      const resp = await askQuestion(q, sessionId);
      setTurns((t) => [...t, { role: "assistant", text: resp.answer, response: resp }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {turns.length === 0 && (
        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold text-gray-700">Try asking</h2>
          <div className="flex flex-col gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => ask(ex)}
                className="rounded-md border border-gray-200 px-3 py-2 text-left text-sm text-gray-700 hover:border-groww-green hover:bg-emerald-50"
              >
                {ex}
              </button>
            ))}
          </div>
        </section>
      )}

      <div className="flex flex-col gap-3">
        {turns.map((turn, i) =>
          turn.role === "user" ? (
            <div key={i} className="self-end rounded-lg bg-groww-green/10 px-4 py-2 max-w-[85%]">
              <p className="text-sm text-gray-800">{turn.text}</p>
            </div>
          ) : (
            <AnswerCard
              key={i}
              answer={turn.text}
              source={turn.response?.source ?? null}
              lastUpdated={turn.response?.last_updated ?? null}
              refused={Boolean(turn.response?.refused)}
            />
          )
        )}
        {loading && (
          <div className="text-sm text-gray-400 animate-pulse">Looking up official sources…</div>
        )}
      </div>

      {error && (
        <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="sticky bottom-4 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a factual question about the five HDFC schemes…"
          className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm shadow-sm outline-none focus:border-groww-green"
          maxLength={1000}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-lg bg-groww-green px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
