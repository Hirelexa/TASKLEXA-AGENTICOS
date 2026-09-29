"use client";

import { useState } from "react";
import { ApiError, transitionMission } from "@/lib/api";
import type { Mission, MissionStatus } from "@/lib/types";
import { MISSION_STATUSES } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

export function OverviewTab({
  mission,
  onMissionChanged,
}: {
  mission: Mission;
  onMissionChanged: (mission: Mission) => void;
}) {
  const [target, setTarget] = useState<MissionStatus>(mission.status);
  const [transitioning, setTransitioning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyTransition = async () => {
    setTransitioning(true);
    setError(null);
    try {
      onMissionChanged(await transitionMission(mission.id, target));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Transition failed.");
    } finally {
      setTransitioning(false);
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(280px,1fr)]">
      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-900">Mission Details</h2>
        <dl className="mt-4 grid gap-4 text-sm">
          <Row label="Description" value={mission.description ?? "—"} />
          <Row label="Constraints" value={(mission.constraints ?? []).join(", ") || "—"} />
          <Row label="Success criteria" value={(mission.success_criteria ?? []).join(", ") || "—"} />
          <Row label="Created by" value={mission.created_by} />
          <Row label="Created at" value={new Date(mission.created_at).toLocaleString()} />
          <Row label="Started at" value={mission.started_at ? new Date(mission.started_at).toLocaleString() : "—"} />
          <Row
            label="Completed at"
            value={mission.completed_at ? new Date(mission.completed_at).toLocaleString() : "—"}
          />
        </dl>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-900">State Machine</h2>
        <p className="mt-2 text-xs text-slate-500">
          Current status: <StatusBadge status={mission.status} />
        </p>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          Transitions are validated server-side against the documented Mission State Machine — an invalid
          transition will be rejected.
        </p>
        <div className="mt-4 flex flex-col gap-2">
          <select
            value={target}
            onChange={(e) => setTarget(e.target.value as MissionStatus)}
            className="input"
          >
            {MISSION_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void applyTransition()}
            disabled={transitioning || target === mission.status}
            className="btn btn-primary"
          >
            {transitioning ? "Transitioning..." : `Transition to ${target}`}
          </button>
        </div>
        {error ? <p className="mt-3 text-sm text-rose-700">{error}</p> : null}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm text-slate-800">{value}</dd>
    </div>
  );
}
