"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, listMissionEvents } from "@/lib/api";
import type { ExecutionEvent } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

export function TimelineTab({ missionId }: { missionId: string }) {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setEvents(await listMissionEvents(missionId));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to load the timeline.");
    }
  }, [missionId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-slate-900">Immutable Execution Event Timeline ({events.length})</h2>
      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}
      <div className="rounded-lg border border-slate-200 bg-white">
        {events.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-slate-500">No events yet.</p>
        ) : (
          <ol className="divide-y divide-slate-100">
            {events.map((event) => (
              <li key={event.id} className="flex flex-col gap-1 px-4 py-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-900">{event.event_type}</span>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={event.status} />
                    <span className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</span>
                  </div>
                </div>
                {event.payload ? (
                  <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2 text-xs text-slate-600">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                ) : null}
                {event.error_category ? (
                  <p className="text-xs text-rose-600">Error category: {event.error_category}</p>
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
