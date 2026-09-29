"use client";

import { useCallback, useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { ApiError, getMission, listVerificationReports, verifyMission } from "@/lib/api";
import type { Mission, VerificationReport } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

export function VerificationTab({
  mission,
  onMissionChanged,
}: {
  mission: Mission;
  onMissionChanged: (mission: Mission) => void;
}) {
  const [reports, setReports] = useState<VerificationReport[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setReports(await listVerificationReports(mission.id));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to load verification reports.");
    }
  }, [mission.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const runVerification = async () => {
    setRunning(true);
    setError(null);
    try {
      await verifyMission(mission.id);
      onMissionChanged(await getMission(mission.id));
      await load();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Verification failed to run.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Verification Reports ({reports.length})</h2>
        <button type="button" onClick={() => void runVerification()} disabled={running} className="btn btn-primary">
          <ShieldCheck className="h-4 w-4" />
          {running ? "Verifying..." : "Run Verification"}
        </button>
      </div>
      <p className="text-xs text-slate-500">
        A mission can only become COMPLETED after an independent verification pass. PASSED completes the
        mission, FAILED fails it, and PARTIAL leaves it in VERIFYING for re-verification.
      </p>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {reports.length === 0 ? (
        <p className="rounded-lg border border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
          No verification reports yet.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {reports.map((report) => (
            <div key={report.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <StatusBadge status={report.verification_status} />
                <span className="text-xs text-slate-500">{new Date(report.created_at).toLocaleString()}</span>
              </div>
              <p className="mt-2 text-xs text-slate-600">Confidence: {report.confidence?.toFixed(2) ?? "—"}</p>
              {report.issues && report.issues.length > 0 ? (
                <ul className="mt-2 list-inside list-disc text-sm text-rose-700">
                  {report.issues.map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                </ul>
              ) : null}
              {report.criteria_results ? (
                <div className="mt-3 grid gap-1 text-xs">
                  {report.criteria_results.map((criterion) => (
                    <div key={criterion.criterion} className="flex items-center gap-2">
                      <span className={criterion.passed ? "text-emerald-700" : "text-rose-700"}>
                        {criterion.passed ? "✓" : "✗"}
                      </span>
                      <span className="font-medium text-slate-700">{criterion.criterion}</span>
                      <span className="text-slate-500">— {criterion.detail}</span>
                      {criterion.informational ? (
                        <span className="text-slate-400">(informational)</span>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
