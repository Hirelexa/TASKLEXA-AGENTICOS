export type IntegrationStatus = "LIVE" | "MOCK" | "NOT_CONFIGURED" | "FAILED" | "UNVERIFIED";

export type IntegrationHealth = {
  provider: string;
  purpose: string;
  status: IntegrationStatus;
  details: string;
  checked_at: string;
};

export type IntegrationsHealthResponse = {
  service: string;
  integrations: IntegrationHealth[];
  checked_at: string;
};

export type MissionStatus =
  | "DRAFT"
  | "PLANNING"
  | "ASSEMBLING"
  | "RUNNING"
  | "WAITING_APPROVAL"
  | "VERIFYING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export const MISSION_STATUSES: MissionStatus[] = [
  "DRAFT",
  "PLANNING",
  "ASSEMBLING",
  "RUNNING",
  "WAITING_APPROVAL",
  "VERIFYING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
];

export type TaskStatus =
  | "PENDING"
  | "READY"
  | "ASSIGNED"
  | "RUNNING"
  | "WAITING_APPROVAL"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type TaskPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";
export type AgentDefinitionStatus = "ACTIVE" | "DISABLED" | "DEPRECATED";
export type ToolStatus = "AVAILABLE" | "NOT_CONFIGURED" | "DISABLED" | "FAILED";
export type DecisionStatus = "OPEN" | "APPROVED" | "REJECTED" | "SUPERSEDED";
export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "MODIFIED";
export type VerificationStatus = "PASSED" | "FAILED" | "PARTIAL";

export type Mission = {
  id: string;
  title: string;
  objective: string;
  description: string | null;
  status: MissionStatus;
  constraints: string[] | null;
  success_criteria: string[] | null;
  created_by: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type Task = {
  id: string;
  mission_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  required_capabilities: string[] | null;
  dependencies: string[] | null;
  assigned_agent: string | null;
  tool_requirements: string[] | null;
  expected_output: string | null;
  actual_output: string | null;
  confidence: number | null;
  created_at: string;
  completed_at: string | null;
};

export type AgentDefinition = {
  id: string;
  name: string;
  description: string;
  capabilities: string[] | null;
  allowed_tools: string[] | null;
  preferred_model_policy: Record<string, unknown> | null;
  permissions: string[] | null;
  risk_level: RiskLevel;
  provider: string;
  status: AgentDefinitionStatus;
};

export type ToolDefinition = {
  id: string;
  name: string;
  description: string;
  provider: string;
  capabilities: string[] | null;
  authentication_type: string | null;
  risk_level: RiskLevel;
  requires_approval: boolean;
  status: ToolStatus;
};

export type Decision = {
  id: string;
  mission_id: string;
  title: string;
  description: string | null;
  options: unknown[] | null;
  recommendation: string | null;
  evidence_ids: string[] | null;
  confidence: number | null;
  risk_level: RiskLevel;
  approval_required: boolean;
  status: DecisionStatus;
};

export type Approval = {
  id: string;
  mission_id: string;
  decision_id: string;
  requested_by: string;
  reason: string | null;
  status: ApprovalStatus;
  approved_by: string | null;
  approved_at: string | null;
  comments: string | null;
};

export type VerificationReport = {
  id: string;
  mission_id: string;
  verification_status: VerificationStatus;
  criteria_results: Array<{
    criterion: string;
    passed: boolean;
    detail: string;
    informational?: boolean;
  }> | null;
  issues: string[] | null;
  confidence: number | null;
  created_at: string;
};

export type ExecutionEvent = {
  id: string;
  mission_id: string;
  task_id: string | null;
  agent_execution_id: string | null;
  correlation_id: string;
  event_type: string;
  provider: string | null;
  status: string;
  error_category: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
};

export type Evidence = {
  id: string;
  mission_id: string;
  task_id: string | null;
  agent_execution_id: string | null;
  source: string;
  source_type: string;
  content: string;
  confidence: number | null;
  demo: boolean;
  created_at: string;
};

export type AgentTeamPlan = {
  mission_id: string;
  required_capabilities: string[];
  selected_agents: string[];
  selected_tools: string[];
  unresolved_capabilities: string[];
  risk_notes: string[];
};

export type TaskDispatchResult = {
  task_id: string;
  status: "DISPATCHED" | "NO_AGENT_AVAILABLE";
  agent_id: string | null;
  detail: string | null;
};

export type TaskReadinessReport = {
  ready_task_ids: string[];
  blocked_task_ids: string[];
  in_progress_task_ids: string[];
  done_task_ids: string[];
  failed_task_ids: string[];
  cyclic_task_ids: string[];
};

export type DispatchReport = {
  mission_id: string;
  readiness: TaskReadinessReport;
  dispatched: TaskDispatchResult[];
  mission_transitioned_to: MissionStatus | null;
};

export type FailTaskResult = {
  task_id: string;
  cascaded_failure_ids: string[];
};

export type GraphNode = {
  id: string;
  labels: string[];
  properties: Record<string, unknown>;
};

export type GraphRelationship = {
  type: string;
  start_id: string;
  end_id: string;
};

export type MissionGraph = {
  mission_id: string;
  nodes: GraphNode[];
  relationships: GraphRelationship[];
};

export type GraphMutationResult = {
  status: "APPLIED" | "FAILED";
  summary: string;
  error: string | null;
};

export type ProjectionReport = {
  mission_id: string;
  applied: number;
  failed: number;
  results: GraphMutationResult[];
};
