"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Zap } from "lucide-react";
import { ApiError, completeTask, createTask, dispatchMission, failTask, listTasks, replanTask } from "@/lib/api";
import type { DispatchReport, Mission, Task } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { Field } from "@/components/dashboard";

export function TasksTab({
  mission,
  onMissionChanged,
}: {
  mission: Mission;
  onMissionChanged: (mission: Mission) => void;
}) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchReport, setDispatchReport] = useState<DispatchReport | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTasks(await listTasks(mission.id));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to load tasks.");
    } finally {
      setLoading(false);
    }
  }, [mission.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const dispatch = async () => {
    setDispatching(true);
    setError(null);
    try {
      const report = await dispatchMission(mission.id);
      setDispatchReport(report);
      await load();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Dispatch failed.");
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Tasks ({tasks.length})</h2>
        <div className="flex gap-2">
          <button type="button" onClick={() => void dispatch()} disabled={dispatching} className="btn btn-primary">
            <Zap className="h-4 w-4" />
            {dispatching ? "Dispatching..." : "Run Dispatch Cycle"}
          </button>
          <button type="button" onClick={() => setShowForm((v) => !v)} className="btn">
            <Plus className="h-4 w-4" />
            New Task
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {dispatchReport ? <DispatchReportPanel report={dispatchReport} /> : null}

      {showForm ? (
        <NewTaskForm
          missionId={mission.id}
          existingTasks={tasks}
          onCreated={() => {
            setShowForm(false);
            void load();
          }}
          onCancel={() => setShowForm(false)}
        />
      ) : null}

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        {tasks.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-slate-500">No tasks yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Capabilities</th>
                <th className="px-4 py-2">Dependencies</th>
                <th className="px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tasks.map((task) => (
                <TaskRow key={task.id} missionId={mission.id} task={task} onChanged={load} />
              ))}
            </tbody>
          </table>
        )}
      </div>
      {mission.status !== "RUNNING" ? (
        <p className="text-xs text-slate-500">
          Note: dispatch does not check mission status by design (see docs/phase-8.md) — it will still run even
          though this mission is {mission.status}, but nothing will be assigned unless there are ready tasks.
        </p>
      ) : null}
    </div>
  );
}

function DispatchReportPanel({ report }: { report: DispatchReport }) {
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm">
      <p className="font-semibold text-blue-900">Dispatch result</p>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-blue-800 md:grid-cols-3">
        <span>Ready: {report.readiness.ready_task_ids.length}</span>
        <span>Blocked: {report.readiness.blocked_task_ids.length}</span>
        <span>In progress: {report.readiness.in_progress_task_ids.length}</span>
        <span>Done: {report.readiness.done_task_ids.length}</span>
        <span>Failed: {report.readiness.failed_task_ids.length}</span>
        <span>Cyclic: {report.readiness.cyclic_task_ids.length}</span>
      </div>
      {report.dispatched.length > 0 ? (
        <ul className="mt-2 list-inside list-disc text-xs text-blue-800">
          {report.dispatched.map((d) => (
            <li key={d.task_id}>
              Task {d.task_id.slice(0, 8)} → {d.status}
              {d.detail ? `: ${d.detail}` : ""}
            </li>
          ))}
        </ul>
      ) : null}
      {report.mission_transitioned_to ? (
        <p className="mt-2 text-xs font-semibold text-blue-900">
          Mission transitioned to {report.mission_transitioned_to}
        </p>
      ) : null}
    </div>
  );
}

function TaskRow({ missionId, task, onChanged }: { missionId: string; task: Task; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showComplete, setShowComplete] = useState(false);
  const [showFail, setShowFail] = useState(false);
  const [output, setOutput] = useState("");
  const [reason, setReason] = useState("");

  const runComplete = async () => {
    setBusy(true);
    setError(null);
    try {
      await completeTask(missionId, task.id, { actual_output: output || undefined });
      setShowComplete(false);
      onChanged();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Complete failed.");
    } finally {
      setBusy(false);
    }
  };

  const runFail = async () => {
    setBusy(true);
    setError(null);
    try {
      await failTask(missionId, task.id, reason);
      setShowFail(false);
      onChanged();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Fail action failed.");
    } finally {
      setBusy(false);
    }
  };

  const runReplan = async () => {
    setBusy(true);
    setError(null);
    try {
      await replanTask(missionId, task.id);
      onChanged();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Replan failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <tr>
        <td className="px-4 py-3">
          <div className="font-medium text-slate-900">{task.title}</div>
          {task.assigned_agent ? (
            <div className="text-xs text-slate-500">Agent: {task.assigned_agent.slice(0, 8)}</div>
          ) : null}
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={task.status} />
        </td>
        <td className="px-4 py-3 text-xs text-slate-600">{(task.required_capabilities ?? []).join(", ") || "—"}</td>
        <td className="px-4 py-3 text-xs text-slate-600">
          {(task.dependencies ?? []).map((d) => d.slice(0, 8)).join(", ") || "—"}
        </td>
        <td className="px-4 py-3">
          <div className="flex gap-1">
            <button
              type="button"
              className="btn"
              disabled={busy || !["ASSIGNED", "RUNNING", "WAITING_APPROVAL"].includes(task.status)}
              onClick={() => setShowComplete((v) => !v)}
            >
              Complete
            </button>
            <button
              type="button"
              className="btn btn-danger"
              disabled={busy || ["COMPLETED", "CANCELLED"].includes(task.status)}
              onClick={() => setShowFail((v) => !v)}
            >
              Fail
            </button>
            <button type="button" className="btn" disabled={busy || task.status !== "FAILED"} onClick={() => void runReplan()}>
              Replan
            </button>
          </div>
        </td>
      </tr>
      {(showComplete || showFail || error) && (
        <tr>
          <td colSpan={5} className="bg-slate-50 px-4 py-3">
            {error ? <p className="mb-2 text-sm text-rose-700">{error}</p> : null}
            {showComplete ? (
              <div className="flex items-end gap-2">
                <Field label="Actual output" className="flex-1">
                  <input value={output} onChange={(e) => setOutput(e.target.value)} className="input" />
                </Field>
                <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void runComplete()}>
                  Confirm Complete
                </button>
              </div>
            ) : null}
            {showFail ? (
              <div className="flex items-end gap-2">
                <Field label="Reason" className="flex-1">
                  <input required value={reason} onChange={(e) => setReason(e.target.value)} className="input" />
                </Field>
                <button type="button" className="btn btn-danger" disabled={busy || !reason} onClick={() => void runFail()}>
                  Confirm Fail
                </button>
              </div>
            ) : null}
          </td>
        </tr>
      )}
    </>
  );
}

function NewTaskForm({
  missionId,
  existingTasks,
  onCreated,
  onCancel,
}: {
  missionId: string;
  existingTasks: Task[];
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  const [requiredCapabilities, setRequiredCapabilities] = useState("");
  const [dependencies, setDependencies] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createTask(missionId, {
        title,
        required_capabilities: requiredCapabilities
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        dependencies,
      });
      onCreated();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to create the task.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-lg border border-slate-200 bg-white p-5">
      <h3 className="text-sm font-semibold text-slate-900">New Task</h3>
      <p className="mt-1 text-xs text-slate-500">
        A task with no required capabilities can never be dispatched — the Capability Resolver matches purely on
        capability, so at least one is required for this task to ever be assigned.
      </p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <Field label="Title" required>
          <input required value={title} onChange={(e) => setTitle(e.target.value)} className="input" />
        </Field>
        <Field label="Required capabilities (comma-separated)" required>
          <input
            required
            value={requiredCapabilities}
            onChange={(e) => setRequiredCapabilities(e.target.value)}
            className="input"
            placeholder="e.g. research"
          />
        </Field>
        {existingTasks.length > 0 ? (
          <Field label="Dependencies" className="md:col-span-2">
            <select
              multiple
              value={dependencies}
              onChange={(e) => setDependencies(Array.from(e.target.selectedOptions, (o) => o.value))}
              className="input"
            >
              {existingTasks.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title}
                </option>
              ))}
            </select>
          </Field>
        ) : null}
      </div>
      {error ? <p className="mt-3 text-sm text-rose-700">{error}</p> : null}
      <div className="mt-4 flex gap-2">
        <button type="submit" disabled={submitting} className="btn btn-primary">
          {submitting ? "Creating..." : "Create Task"}
        </button>
        <button type="button" onClick={onCancel} className="btn">
          Cancel
        </button>
      </div>
    </form>
  );
}
