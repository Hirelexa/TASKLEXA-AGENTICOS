"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, RefreshCw } from "lucide-react";
import { ApiError, API_BASE_URL, createMission, getIntegrationsHealth, listMissions } from "@/lib/api";
import type { IntegrationsHealthResponse, Mission } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

export function Dashboard() {
  const router = useRouter();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [health, setHealth] = useState<IntegrationsHealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [missionList, integrationHealth] = await Promise.all([listMissions(), getIntegrationsHealth()]);
      setMissions(missionList);
      setHealth(integrationHealth);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to reach the API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const liveCount = health?.integrations.filter((i) => i.status === "LIVE").length ?? 0;
  const attentionCount = health ? health.integrations.length - liveCount : 0;

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-6 lg:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">Mission Control</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Missions</h1>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-800 shadow-sm hover:bg-slate-50 disabled:cursor-wait disabled:opacity-70"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-blue-700 px-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-800"
          >
            <Plus className="h-4 w-4" />
            New Mission
          </button>
        </div>
      </header>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {showForm ? (
        <NewMissionForm
          onCreated={(mission) => {
            setShowForm(false);
            router.push(`/missions/${mission.id}`);
          }}
          onCancel={() => setShowForm(false)}
        />
      ) : null}

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.6fr)]">
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-900">All Missions ({missions.length})</h2>
          </div>
          {missions.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-slate-500">
              No missions yet. Create one to get started.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Title</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {missions.map((mission) => (
                  <tr
                    key={mission.id}
                    className="cursor-pointer hover:bg-slate-50"
                    onClick={() => router.push(`/missions/${mission.id}`)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{mission.title}</div>
                      <div className="text-xs text-slate-500">{mission.objective}</div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={mission.status} />
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {new Date(mission.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-900">Integration Health</h2>
            <p className="mt-1 text-xs text-slate-500">
              {liveCount} live &middot; {attentionCount} not live &middot; API {API_BASE_URL}
            </p>
          </div>
          <div className="divide-y divide-slate-100">
            {(health?.integrations ?? []).map((item) => (
              <div key={item.provider} className="px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">{item.provider}</h3>
                    <p className="text-xs text-slate-500">{item.purpose}</p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-500">{item.details}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function NewMissionForm({
  onCreated,
  onCancel,
}: {
  onCreated: (mission: Mission) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [description, setDescription] = useState("");
  const [createdBy, setCreatedBy] = useState("operator");
  const [successCriteria, setSuccessCriteria] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const mission = await createMission({
        title,
        objective,
        description: description || undefined,
        created_by: createdBy,
        success_criteria: successCriteria
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      onCreated(mission);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to create the mission.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-slate-900">New Mission</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Field label="Title" required>
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="input"
            placeholder="Launch competitive analysis"
          />
        </Field>
        <Field label="Created by" required>
          <input
            required
            value={createdBy}
            onChange={(e) => setCreatedBy(e.target.value)}
            className="input"
          />
        </Field>
        <Field label="Objective" required className="md:col-span-2">
          <input
            required
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            className="input"
            placeholder="What should this mission accomplish?"
          />
        </Field>
        <Field label="Description" className="md:col-span-2">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="input" rows={2} />
        </Field>
        <Field label="Success criteria (comma-separated)" className="md:col-span-2">
          <input
            value={successCriteria}
            onChange={(e) => setSuccessCriteria(e.target.value)}
            className="input"
            placeholder="e.g. identify 3 competitors, must reduce churn by 10%"
          />
        </Field>
      </div>
      {error ? <p className="mt-3 text-sm text-rose-700">{error}</p> : null}
      <div className="mt-4 flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex h-9 items-center rounded-md bg-blue-700 px-3 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-70"
        >
          {submitting ? "Creating..." : "Create Mission"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export function Field({
  label,
  children,
  required,
  className = "",
}: {
  label: string;
  children: React.ReactNode;
  required?: boolean;
  className?: string;
}) {
  return (
    <label className={`flex flex-col gap-1 text-xs font-medium text-slate-600 ${className}`}>
      <span>
        {label}
        {required ? <span className="text-rose-600"> *</span> : null}
      </span>
      {children}
    </label>
  );
}
