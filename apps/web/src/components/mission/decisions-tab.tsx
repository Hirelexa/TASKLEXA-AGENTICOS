"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { ApiError, createDecision, getMission, listApprovals, listDecisions, resolveApproval } from "@/lib/api";
import type { Approval, Decision, Mission } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { Field } from "@/components/dashboard";

export function DecisionsTab({
  mission,
  onMissionChanged,
}: {
  mission: Mission;
  onMissionChanged: (mission: Mission) => void;
}) {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [decisionList, approvalList] = await Promise.all([
        listDecisions(mission.id),
        listApprovals(mission.id),
      ]);
      setDecisions(decisionList);
      setApprovals(approvalList);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to load decisions.");
    }
  }, [mission.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const approvalFor = (decisionId: string) => approvals.find((a) => a.decision_id === decisionId);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Decisions ({decisions.length})</h2>
        <button type="button" onClick={() => setShowForm((v) => !v)} className="btn btn-primary">
          <Plus className="h-4 w-4" />
          New Decision
        </button>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {showForm ? (
        <NewDecisionForm
          missionId={mission.id}
          onCreated={(mission_) => {
            setShowForm(false);
            onMissionChanged(mission_);
            void load();
          }}
          onCancel={() => setShowForm(false)}
        />
      ) : null}

      {decisions.length === 0 ? (
        <p className="rounded-lg border border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
          No decisions yet.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {decisions.map((decision) => (
            <DecisionCard
              key={decision.id}
              mission={mission}
              decision={decision}
              approval={approvalFor(decision.id)}
              onChanged={(mission_) => {
                onMissionChanged(mission_);
                void load();
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function DecisionCard({
  mission,
  decision,
  approval,
  onChanged,
}: {
  mission: Mission;
  decision: Decision;
  approval: Approval | undefined;
  onChanged: (mission: Mission) => void;
}) {
  const [approvedBy, setApprovedBy] = useState("human-operator");
  const [comments, setComments] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const act = async (action: "approve" | "modify" | "reject") => {
    if (!approval) return;
    setBusy(true);
    setError(null);
    try {
      await resolveApproval(mission.id, approval.id, action, { approved_by: approvedBy, comments: comments || undefined });
      onChanged(await getMission(mission.id));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Approval action failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{decision.title}</h3>
          {decision.description ? <p className="mt-1 text-xs text-slate-500">{decision.description}</p> : null}
        </div>
        <div className="flex gap-2">
          <StatusBadge status={decision.status} />
          <StatusBadge status={decision.risk_level} />
        </div>
      </div>

      {approval ? (
        <div className="mt-3 rounded-md border border-slate-100 bg-slate-50 p-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-700">
              Approval requested by {approval.requested_by}
              {approval.reason ? ` — ${approval.reason}` : ""}
            </p>
            <StatusBadge status={approval.status} />
          </div>
          {approval.status === "PENDING" ? (
            <div className="mt-2 flex flex-wrap items-end gap-2">
              <Field label="Approved by">
                <input value={approvedBy} onChange={(e) => setApprovedBy(e.target.value)} className="input" />
              </Field>
              <Field label="Comments" className="flex-1">
                <input value={comments} onChange={(e) => setComments(e.target.value)} className="input" />
              </Field>
              <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void act("approve")}>
                Approve
              </button>
              <button type="button" className="btn" disabled={busy} onClick={() => void act("modify")}>
                Modify
              </button>
              <button type="button" className="btn btn-danger" disabled={busy} onClick={() => void act("reject")}>
                Reject
              </button>
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-500">
              Resolved by {approval.approved_by} at{" "}
              {approval.approved_at ? new Date(approval.approved_at).toLocaleString() : "—"}
              {approval.comments ? ` — ${approval.comments}` : ""}
            </p>
          )}
          {error ? <p className="mt-2 text-sm text-rose-700">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

function NewDecisionForm({
  missionId,
  onCreated,
  onCancel,
}: {
  missionId: string;
  onCreated: (mission: Mission) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  const [approvalRequired, setApprovalRequired] = useState(false);
  const [requestedBy, setRequestedBy] = useState("planning-agent");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createDecision(missionId, {
        title,
        approval_required: approvalRequired,
        requested_by: requestedBy,
        approval_reason: reason || undefined,
      });
      onCreated(await getMission(missionId));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to create the decision.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-lg border border-slate-200 bg-white p-5">
      <h3 className="text-sm font-semibold text-slate-900">New Decision</h3>
      <p className="mt-1 text-xs text-slate-500">
        Requiring approval moves this mission to WAITING_APPROVAL and blocks dispatch — only valid while the
        mission is RUNNING.
      </p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <Field label="Title" required className="md:col-span-2">
          <input required value={title} onChange={(e) => setTitle(e.target.value)} className="input" />
        </Field>
        <Field label="Requested by" required>
          <input required value={requestedBy} onChange={(e) => setRequestedBy(e.target.value)} className="input" />
        </Field>
        <label className="mt-5 flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={approvalRequired}
            onChange={(e) => setApprovalRequired(e.target.checked)}
          />
          Requires human approval
        </label>
        {approvalRequired ? (
          <Field label="Approval reason" className="md:col-span-2">
            <input value={reason} onChange={(e) => setReason(e.target.value)} className="input" />
          </Field>
        ) : null}
      </div>
      {error ? <p className="mt-3 text-sm text-rose-700">{error}</p> : null}
      <div className="mt-4 flex gap-2">
        <button type="submit" disabled={submitting} className="btn btn-primary">
          {submitting ? "Creating..." : "Create Decision"}
        </button>
        <button type="button" onClick={onCancel} className="btn">
          Cancel
        </button>
      </div>
    </form>
  );
}
