"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { Activity, GitBranch, RefreshCw, ShieldCheck } from "lucide-react";

type IntegrationStatus = "LIVE" | "MOCK" | "NOT_CONFIGURED" | "FAILED";

type IntegrationHealth = {
  provider: string;
  purpose: string;
  status: IntegrationStatus;
  details: string;
  checked_at: string;
};

type IntegrationsHealthResponse = {
  service: string;
  integrations: IntegrationHealth[];
  checked_at: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const fallbackIntegrations: IntegrationHealth[] = [
  {
    provider: "API",
    purpose: "FastAPI control plane",
    status: "NOT_CONFIGURED",
    details: "Waiting for /health/integrations.",
    checked_at: new Date().toISOString(),
  },
];

const statusStyles: Record<IntegrationStatus, string> = {
  LIVE: "border-emerald-200 bg-emerald-50 text-emerald-700",
  MOCK: "border-violet-200 bg-violet-50 text-violet-700",
  NOT_CONFIGURED: "border-slate-200 bg-slate-100 text-slate-600",
  FAILED: "border-rose-200 bg-rose-50 text-rose-700",
};

export function MissionControlShell() {
  const [health, setHealth] = useState<IntegrationsHealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/health/integrations`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`Health request failed with HTTP ${response.status}`);
      }

      setHealth((await response.json()) as IntegrationsHealthResponse);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Unable to read integration health.");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadHealth();
  }, [loadHealth]);

  const integrations = health?.integrations ?? fallbackIntegrations;
  const liveCount = integrations.filter((item) => item.status === "LIVE").length;
  const attentionCount = integrations.filter((item) => item.status !== "LIVE").length;

  const graph = useMemo(() => buildPhaseOneGraph(integrations), [integrations]);

  return (
    <main className="min-h-screen bg-[#f6f7f9] text-slate-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-5 lg:px-8">
        <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">Mission Control</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal text-slate-950">Tasklexa Agenticos</h1>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
              Phase 1 local infrastructure scaffold. External providers stay explicit until live verification exists.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadHealth()}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-800 shadow-sm transition hover:bg-slate-50 disabled:cursor-wait disabled:opacity-70"
            disabled={loading}
            title="Refresh integration health"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <Metric label="Local live services" value={String(liveCount)} icon={<Activity className="h-5 w-5" />} />
          <Metric label="Needs attention" value={String(attentionCount)} icon={<ShieldCheck className="h-5 w-5" />} />
          <Metric label="API target" value={API_BASE_URL} icon={<GitBranch className="h-5 w-5" />} compact />
        </section>

        {error ? (
          <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-4 py-3">
              <h2 className="text-sm font-semibold text-slate-900">Local Mission Graph Scaffold</h2>
            </div>
            <div className="h-[520px]">
              <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView proOptions={{ hideAttribution: true }}>
                <Background />
                <MiniMap pannable zoomable />
                <Controls />
              </ReactFlow>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-4 py-3">
              <h2 className="text-sm font-semibold text-slate-900">Integration Health</h2>
            </div>
            <div className="divide-y divide-slate-100">
              {integrations.map((item) => (
                <div key={item.provider} className="px-4 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900">{item.provider}</h3>
                      <p className="mt-1 text-sm text-slate-600">{item.purpose}</p>
                    </div>
                    <span className={`rounded border px-2 py-1 text-xs font-semibold ${statusStyles[item.status]}`}>
                      {item.status}
                    </span>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-slate-500">{item.details}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({
  label,
  value,
  icon,
  compact = false,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  compact?: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-3 text-slate-500">
        {icon}
        <span className="text-xs font-semibold uppercase tracking-[0.12em]">{label}</span>
      </div>
      <p className={`mt-3 font-semibold text-slate-950 ${compact ? "break-all text-sm" : "text-3xl"}`}>{value}</p>
    </div>
  );
}

function buildPhaseOneGraph(integrations: IntegrationHealth[]): { nodes: Node[]; edges: Edge[] } {
  const statusFor = (provider: string): IntegrationStatus =>
    integrations.find((item) => item.provider === provider)?.status ?? "NOT_CONFIGURED";

  const nodes: Node[] = [
    phaseNode("mission-control", "Mission Control", "LIVE", 0, 120),
    phaseNode("api", "FastAPI Control Plane", statusFor("API") === "FAILED" ? "FAILED" : "LIVE", 260, 120),
    phaseNode("postgres", "PostgreSQL", statusFor("PostgreSQL"), 560, 0),
    phaseNode("redis", "Redis", statusFor("Redis"), 560, 120),
    phaseNode("neo4j", "Neo4j", statusFor("Neo4j"), 560, 240),
    phaseNode("band", "Band", statusFor("Band"), 860, 0),
    phaseNode("openrouter", "OpenRouter", statusFor("OpenRouter"), 860, 120),
    phaseNode("similarweb", "Similarweb", statusFor("Similarweb"), 860, 240),
  ];

  const edges: Edge[] = [
    { id: "web-api", source: "mission-control", target: "api" },
    { id: "api-postgres", source: "api", target: "postgres" },
    { id: "api-redis", source: "api", target: "redis" },
    { id: "api-neo4j", source: "api", target: "neo4j" },
    { id: "api-band", source: "api", target: "band" },
    { id: "api-openrouter", source: "api", target: "openrouter" },
    { id: "api-similarweb", source: "api", target: "similarweb" },
  ];

  return { nodes, edges };
}

function phaseNode(id: string, label: string, status: IntegrationStatus, x: number, y: number): Node {
  return {
    id,
    position: { x, y },
    data: {
      label: (
        <div className="min-w-40">
          <div className="text-sm font-semibold text-slate-900">{label}</div>
          <div className={`mt-2 inline-flex rounded border px-2 py-1 text-[10px] font-semibold ${statusStyles[status]}`}>
            {status}
          </div>
        </div>
      ),
    },
    style: {
      border: "1px solid #cbd5e1",
      borderRadius: 8,
      padding: 10,
      background: "#ffffff",
      width: 190,
    },
  };
}

