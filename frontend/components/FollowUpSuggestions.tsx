"use client";

interface FollowUpSuggestionsProps {
  questions: string[];
  onAsk: (q: string) => void;
}

export function FollowUpSuggestions({ questions, onAsk }: FollowUpSuggestionsProps) {
  return (
    <section className="rounded-lg border border-line bg-surface p-4">
      <h2 className="mb-2 text-sm font-semibold text-ink">You might also ask</h2>
      <div className="flex flex-col gap-2">
        {questions.map((q) => (
          <button
            key={q}
            onClick={() => onAsk(q)}
            className="rounded-md border border-line px-3 py-2 text-left text-sm text-muted hover:border-groww-green hover:bg-emerald-500/10"
          >
            {q}
          </button>
        ))}
      </div>
    </section>
  );
}
