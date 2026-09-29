"use client";

import { useEffect, useState } from "react";
import { ApiError, listAgents, listTools, resolveTeamPlan } from "@/lib/api";
import type { AgentDefinition, AgentTeamPlan, Mission, ToolDefinition } from "@/lib/types";
import { Field } from "@/components/dashboard";

export function TeamTab({ mission }: { mission: Mission }) {
  const [capabilities, setCapabilities] = useState("");
  const [plan, setPlan] = useState<AgentTeamPlan | null>(null);
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listAgents().then(setAgents).catch(() => undefined);
    void listTools().then(setTools).catch(() => undefined);
  }, []);

  const agentName = (id: string) => agents.find((a) => a.id === id)?.name ?? id.slice(0, 8);
  const toolName = (id: string) => tools.find((t) => t.id === id)?.name ?? id.slice(0, 8);

  const resolve = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const required = capabilities
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      setPlan(await resolveTeamPlan(mission.id, required));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to resolve a team plan.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={resolve} className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-900">Resolve Capability Team</h2>
        <p className="mt-1 text-xs text-slate-500">
          Enter the capabilities this mission needs; the Capability Resolver matches them against active agents
          and available tools.
        </p>
        <div className="mt-3 flex items-end gap-2">
          <Field label="Required capabilities (comma-separated)" className="flex-1">
            <input
              value={capabilities}
              onChange={(e) => setCapabilities(e.target.value)}
              className="input"
              placeholder="e.g. research, planning, digital_market_intelligence"
            />
          </Field>
          <button type="submit" disabled={submitting} className="btn btn-primary">
            {submitting ? "Resolving..." : "Resolve"}
          </button>
        </div>
        {error ? <p className="mt-3 text-sm text-rose-700">{error}</p> : null}
      </form>

      {plan ? (
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-900">Resolution Result</h3>
          <div className="mt-3 grid gap-3 text-sm md:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Selected Agents</p>
              {plan.selected_agents.length === 0 ? (
                <p className="mt-1 text-slate-500">None</p>
              ) : (
                <ul className="mt-1 list-inside list-disc text-slate-800">
                  {plan.selected_agents.map((id) => (
                    <li key={id}>{agentName(id)}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Selected Tools</p>
              {plan.selected_tools.length === 0 ? (
                <p className="mt-1 text-slate-500">None</p>
              ) : (
                <ul className="mt-1 list-inside list-disc text-slate-800">
                  {plan.selected_tools.map((id) => (
                    <li key={id}>{toolName(id)}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          {plan.unresolved_capabilities.length > 0 ? (
            <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Unresolved capabilities: {plan.unresolved_capabilities.join(", ")}
            </div>
          ) : null}
          {plan.risk_notes.length > 0 ? (
            <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {plan.risk_notes.map((note, i) => (
                <p key={i}>{note}</p>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
