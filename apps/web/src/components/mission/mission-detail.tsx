"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { ApiError, getMission } from "@/lib/api";
import type { Mission } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { OverviewTab } from "@/components/mission/overview-tab";
import { TasksTab } from "@/components/mission/tasks-tab";
import { TeamTab } from "@/components/mission/team-tab";
import { DecisionsTab } from "@/components/mission/decisions-tab";
import { EvidenceTab } from "@/components/mission/evidence-tab";
import { TimelineTab } from "@/components/mission/timeline-tab";
import { VerificationTab } from "@/components/mission/verification-tab";
import { GraphTab } from "@/components/mission/graph-tab";

const TABS = [
  "Overview",
  "Tasks",
  "Team",
  "Decisions & Approvals",
  "Evidence",
  "Timeline",
  "Verification",
  "Graph",
] as const;

type Tab = (typeof TABS)[number];

export function MissionDetail({ missionId }: { missionId: string }) {
  const [mission, setMission] = useState<Mission | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  const loadMission = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setMission(await getMission(missionId));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to load this mission.");
    } finally {
      setLoading(false);
    }
  }, [missionId]);

  useEffect(() => {
    void loadMission();
  }, [loadMission]);

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6 lg:px-8">
      <Link href="/" className="inline-flex items-center gap-1 text-sm font-medium text-blue-700 hover:underline">
        <ArrowLeft className="h-4 w-4" />
        All missions
      </Link>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {mission ? (
        <>
          <header className="flex flex-col gap-3 border-b border-slate-200 pb-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-semibold text-slate-950">{mission.title}</h1>
                <StatusBadge status={mission.status} />
              </div>
              <p className="mt-1 max-w-2xl text-sm text-slate-600">{mission.objective}</p>
            </div>
            <button
              type="button"
              onClick={() => void loadMission()}
              className="btn"
              disabled={loading}
              title="Refresh mission"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </header>

          <nav className="flex flex-wrap gap-1 border-b border-slate-200">
            {TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded-t-md px-3 py-2 text-sm font-medium transition ${
                  activeTab === tab
                    ? "border-b-2 border-blue-700 text-blue-700"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>

          <div>
            {activeTab === "Overview" && <OverviewTab mission={mission} onMissionChanged={setMission} />}
            {activeTab === "Tasks" && <TasksTab mission={mission} onMissionChanged={setMission} />}
            {activeTab === "Team" && <TeamTab mission={mission} />}
            {activeTab === "Decisions & Approvals" && (
              <DecisionsTab mission={mission} onMissionChanged={setMission} />
            )}
            {activeTab === "Evidence" && <EvidenceTab missionId={mission.id} />}
            {activeTab === "Timeline" && <TimelineTab missionId={mission.id} />}
            {activeTab === "Verification" && <VerificationTab mission={mission} onMissionChanged={setMission} />}
            {activeTab === "Graph" && <GraphTab missionId={mission.id} />}
          </div>
        </>
      ) : loading ? (
        <p className="text-sm text-slate-500">Loading mission...</p>
      ) : null}
    </main>
  );
}
