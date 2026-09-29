"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, listEvidence } from "@/lib/api";
import type { Evidence } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

export function EvidenceTab({ missionId }: { missionId: string }) {
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setEvidence(await listEvidence(missionId));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to load evidence.");
    }
  }, [missionId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-slate-900">Evidence ({evidence.length})</h2>
      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}
      {evidence.length === 0 ? (
        <p className="rounded-lg border border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
          No evidence recorded for this mission yet. There is no evidence-creation API in this build — evidence
          gets recorded by an Agent Runtime, which doesn&apos;t exist in this codebase yet.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {evidence.map((item) => (
            <div key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    {item.source} <span className="text-xs font-normal text-slate-500">({item.source_type})</span>
                  </p>
                  <p className="mt-1 text-sm text-slate-700">{item.content}</p>
                </div>
                {item.demo ? <StatusBadge status="MOCK" /> : null}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Confidence: {item.confidence ?? "—"} &middot; {new Date(item.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
