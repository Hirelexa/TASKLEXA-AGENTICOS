import type {
  AgentDefinition,
  AgentTeamPlan,
  Approval,
  Decision,
  DispatchReport,
  Evidence,
  ExecutionEvent,
  FailTaskResult,
  IntegrationsHealthResponse,
  Mission,
  MissionGraph,
  MissionStatus,
  ProjectionReport,
  Task,
  TaskPriority,
  ToolDefinition,
  VerificationReport,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body);
    } catch {
      // response had no JSON body; keep the generic detail
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined });
}

// --- Health -----------------------------------------------------------

export function getIntegrationsHealth(): Promise<IntegrationsHealthResponse> {
  return request("/health/integrations");
}

// --- Missions -----------------------------------------------------------

export function listMissions(): Promise<Mission[]> {
  return request("/missions");
}

export function getMission(missionId: string): Promise<Mission> {
  return request(`/missions/${missionId}`);
}

export function createMission(input: {
  title: string;
  objective: string;
  description?: string;
  created_by: string;
  constraints?: string[];
  success_criteria?: string[];
}): Promise<Mission> {
  return post("/missions", input);
}

export function transitionMission(missionId: string, status: MissionStatus): Promise<Mission> {
  return post(`/missions/${missionId}/transitions`, { status });
}

export function listMissionEvents(missionId: string): Promise<ExecutionEvent[]> {
  return request(`/missions/${missionId}/events`);
}

export function resolveTeamPlan(missionId: string, requiredCapabilities: string[]): Promise<AgentTeamPlan> {
  return post(`/missions/${missionId}/team-plan`, { required_capabilities: requiredCapabilities });
}

export function projectMissionGraph(missionId: string): Promise<ProjectionReport> {
  return post(`/missions/${missionId}/graph/project`);
}

export function getMissionGraph(missionId: string): Promise<MissionGraph> {
  return request(`/missions/${missionId}/graph`);
}

export function verifyMission(missionId: string): Promise<VerificationReport> {
  return post(`/missions/${missionId}/verify`);
}

export function listVerificationReports(missionId: string): Promise<VerificationReport[]> {
  return request(`/missions/${missionId}/verification-reports`);
}

// --- Tasks -----------------------------------------------------------

export function listTasks(missionId: string): Promise<Task[]> {
  return request(`/missions/${missionId}/tasks`);
}

export function createTask(
  missionId: string,
  input: {
    title: string;
    description?: string;
    priority?: TaskPriority;
    required_capabilities?: string[];
    dependencies?: string[];
    expected_output?: string;
  },
): Promise<Task> {
  return post(`/missions/${missionId}/tasks`, { mission_id: missionId, ...input });
}

export function completeTask(
  missionId: string,
  taskId: string,
  input: { actual_output?: string; confidence?: number },
): Promise<Task> {
  return post(`/missions/${missionId}/tasks/${taskId}/complete`, input);
}

export function failTask(missionId: string, taskId: string, reason: string): Promise<FailTaskResult> {
  return post(`/missions/${missionId}/tasks/${taskId}/fail`, { reason });
}

export function replanTask(missionId: string, taskId: string): Promise<Task> {
  return post(`/missions/${missionId}/tasks/${taskId}/replan`);
}

export function dispatchMission(missionId: string): Promise<DispatchReport> {
  return post(`/missions/${missionId}/orchestrator/dispatch`);
}

// --- Agents & Tools -----------------------------------------------------------

export function listAgents(): Promise<AgentDefinition[]> {
  return request("/agents");
}

export function createAgent(input: {
  name: string;
  description: string;
  provider: string;
  capabilities?: string[];
  allowed_tools?: string[];
  permissions?: string[];
  risk_level?: string;
}): Promise<AgentDefinition> {
  return post("/agents", input);
}

export function listTools(): Promise<ToolDefinition[]> {
  return request("/tools");
}

// --- Decisions & Approvals -----------------------------------------------------------

export function listDecisions(missionId: string): Promise<Decision[]> {
  return request(`/missions/${missionId}/decisions`);
}

export function createDecision(
  missionId: string,
  input: {
    title: string;
    description?: string;
    approval_required?: boolean;
    requested_by: string;
    approval_reason?: string;
    risk_level?: string;
  },
): Promise<Decision> {
  return post(`/missions/${missionId}/decisions`, { mission_id: missionId, ...input });
}

export function listApprovals(missionId: string): Promise<Approval[]> {
  return request(`/missions/${missionId}/approvals`);
}

export function resolveApproval(
  missionId: string,
  approvalId: string,
  action: "approve" | "modify" | "reject",
  input: { approved_by: string; comments?: string },
): Promise<Approval> {
  return post(`/missions/${missionId}/approvals/${approvalId}/${action}`, input);
}

// --- Evidence -----------------------------------------------------------

export function listEvidence(missionId: string): Promise<Evidence[]> {
  return request(`/missions/${missionId}/evidence`);
}
