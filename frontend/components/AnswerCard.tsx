"use client";

import { SourceInfo } from "@/types";

export function AnswerCard({
  answer,
  source,
  lastUpdated,
  refused,
}: {
  answer: string;
  source: SourceInfo | null;
  lastUpdated: string | null;
  refused: boolean;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {refused && (
        <div className="mb-2 inline-block rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
          Facts-only assistant
        </div>
      )}
      <p className="whitespace-pre-line text-sm leading-relaxed text-gray-800">{answer}</p>

      {source?.url && (
        <div className="mt-3 border-t border-gray-100 pt-3 text-xs text-gray-600">
          <span className="font-semibold">Source: </span>
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-groww-green underline break-all"
          >
            {source.title || source.url}
          </a>
          {source.page != null && <span> — page {source.page}</span>}
        </div>
      )}

      {lastUpdated && (
        <div className="mt-1 text-xs text-gray-500">{lastUpdated}</div>
      )}
    </div>
  );
}
