"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { ApiError, createAgent, listAgents, listTools } from "@/lib/api";
import type { AgentDefinition, ToolDefinition } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { Field } from "@/components/dashboard";

export function AgentsRegistry() {
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [agentList, toolList] = await Promise.all([listAgents(), listTools()]);
      setAgents(agentList);
      setTools(toolList);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to reach the API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-6 lg:px-8">
      <header className="flex items-center justify-between border-b border-slate-200 pb-5">
        <h1 className="text-3xl font-semibold text-slate-950">Agents &amp; Tools</h1>
        <div className="flex gap-2">
          <button type="button" onClick={() => void load()} className="btn" disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button type="button" onClick={() => setShowForm((v) => !v)} className="btn btn-primary">
            <Plus className="h-4 w-4" />
            New Agent
          </button>
        </div>
      </header>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {showForm ? (
        <NewAgentForm
          onCreated={() => {
            setShowForm(false);
            void load();
          }}
          onCancel={() => setShowForm(false)}
        />
      ) : null}

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">Agent Registry ({agents.length})</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Capabilities</th>
              <th className="px-4 py-2">Risk</th>
              <th className="px-4 py-2">Provider</th>
              <th className="px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {agents.map((agent) => (
              <tr key={agent.id}>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-900">{agent.name}</div>
                  <div className="text-xs text-slate-500">{agent.description}</div>
                </td>
                <td className="px-4 py-3 text-xs text-slate-600">
                  {(agent.capabilities ?? []).join(", ") || "—"}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={agent.risk_level} />
                </td>
                <td className="px-4 py-3 text-xs text-slate-600">{agent.provider}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={agent.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">Tool Registry ({tools.length})</h2>
        </div>
        {tools.length === 0 ? (
          <p className="px-4 py-6 text-sm text-slate-500">No tools registered.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Capabilities</th>
                <th className="px-4 py-2">Requires Approval</th>
                <th className="px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tools.map((tool) => (
                <tr key={tool.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{tool.name}</div>
                    <div className="text-xs text-slate-500">{tool.description}</div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600">{(tool.capabilities ?? []).join(", ") || "—"}</td>
                  <td className="px-4 py-3 text-xs text-slate-600">{tool.requires_approval ? "Yes" : "No"}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={tool.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}

function NewAgentForm({ onCreated, onCancel }: { onCreated: () => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [provider, setProvider] = useState("tasklexa-internal");
  const [capabilities, setCapabilities] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createAgent({
        name,
        description,
        provider,
        capabilities: capabilities
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      onCreated();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to create the agent.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-slate-900">New Agent Definition</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Field label="Name" required>
          <input required value={name} onChange={(e) => setName(e.target.value)} className="input" />
        </Field>
        <Field label="Provider" required>
          <input required value={provider} onChange={(e) => setProvider(e.target.value)} className="input" />
        </Field>
        <Field label="Description" required className="md:col-span-2">
          <input required value={description} onChange={(e) => setDescription(e.target.value)} className="input" />
        </Field>
        <Field label="Capabilities (comma-separated)" className="md:col-span-2">
          <input
            value={capabilities}
            onChange={(e) => setCapabilities(e.target.value)}
            className="input"
            placeholder="e.g. research, summarization"
          />
        </Field>
      </div>
      {error ? <p className="mt-3 text-sm text-rose-700">{error}</p> : null}
      <div className="mt-4 flex gap-2">
        <button type="submit" disabled={submitting} className="btn btn-primary">
          {submitting ? "Creating..." : "Create Agent"}
        </button>
        <button type="button" onClick={onCancel} className="btn">
          Cancel
        </button>
      </div>
    </form>
  );
}
