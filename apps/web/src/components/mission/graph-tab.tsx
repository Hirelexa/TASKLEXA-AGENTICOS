"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { Share2 } from "lucide-react";
import { ApiError, getMissionGraph, projectMissionGraph } from "@/lib/api";
import type { MissionGraph, ProjectionReport } from "@/lib/types";

const LABEL_COLUMN: Record<string, number> = {
  Mission: 0,
  Task: 1,
  Agent: 2,
  Capability: 2,
  Tool: 2,
  Evidence: 3,
  Decision: 4,
  Approval: 5,
  Outcome: 6,
};

export function GraphTab({ missionId }: { missionId: string }) {
  const [graph, setGraph] = useState<MissionGraph | null>(null);
  const [projecting, setProjecting] = useState(false);
  const [projectionReport, setProjectionReport] = useState<ProjectionReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setGraph(await getMissionGraph(missionId));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Unable to load the mission graph.");
    }
  }, [missionId]);

  useEffect(() => {
    void load();
  }, [load]);

  const project = async () => {
    setProjecting(true);
    setError(null);
    try {
      setProjectionReport(await projectMissionGraph(missionId));
      await load();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Graph projection failed.");
    } finally {
      setProjecting(false);
    }
  };

  const { nodes, edges } = useMemo(() => buildFlowGraph(graph), [graph]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">
          Mission Graph ({graph?.nodes.length ?? 0} nodes, {graph?.relationships.length ?? 0} relationships)
        </h2>
        <button type="button" onClick={() => void project()} disabled={projecting} className="btn btn-primary">
          <Share2 className="h-4 w-4" />
          {projecting ? "Projecting..." : "Project / Repair Graph"}
        </button>
      </div>
      <p className="text-xs text-slate-500">
        PostgreSQL is authoritative; this graph is a Neo4j projection. Projection is idempotent, so this button
        both builds it the first time and repairs it after any failure.
      </p>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {projectionReport ? (
        <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-xs text-blue-800">
          Applied {projectionReport.applied}, failed {projectionReport.failed}
        </div>
      ) : null}

      <div className="h-[560px] overflow-hidden rounded-lg border border-slate-200 bg-white">
        {nodes.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            No graph data yet — click &ldquo;Project / Repair Graph&rdquo; to build it from PostgreSQL.
          </div>
        ) : (
          <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
            <Background />
            <MiniMap pannable zoomable />
            <Controls />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}

function buildFlowGraph(graph: MissionGraph | null): { nodes: Node[]; edges: Edge[] } {
  if (!graph) return { nodes: [], edges: [] };

  const columnCounts: Record<number, number> = {};
  const nodes: Node[] = graph.nodes.map((node) => {
    const primaryLabel = node.labels[0] ?? "Unknown";
    const column = LABEL_COLUMN[primaryLabel] ?? 7;
    const row = columnCounts[column] ?? 0;
    columnCounts[column] = row + 1;

    const name = (node.properties.title ?? node.properties.name ?? node.properties.source ?? node.id) as string;

    return {
      id: node.id,
      position: { x: column * 220, y: row * 110 },
      data: {
        label: (
          <div className="min-w-36">
            <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{primaryLabel}</div>
            <div className="text-sm font-medium text-slate-900">{String(name).slice(0, 40)}</div>
            {node.properties.status ? (
              <div className="mt-1 text-[10px] text-slate-500">{String(node.properties.status)}</div>
            ) : null}
          </div>
        ),
      },
      style: {
        border: "1px solid #cbd5e1",
        borderRadius: 8,
        padding: 8,
        background: "#ffffff",
        width: 190,
      },
    };
  });

  const edges: Edge[] = graph.relationships.map((rel, index) => ({
    id: `${rel.start_id}-${rel.type}-${rel.end_id}-${index}`,
    source: rel.start_id,
    target: rel.end_id,
    label: rel.type,
    labelStyle: { fontSize: 10 },
  }));

  return { nodes, edges };
}
