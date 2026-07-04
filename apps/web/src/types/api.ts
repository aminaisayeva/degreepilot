export interface Course {
  code: string;
  title: string;
  department: string;
  credits: number;
  description: string;
  workload_level: number;
  offered_terms: string[];
  prerequisites: string[][];
  categories: string[];
  career_tags: string[];
}

export interface Requirement {
  id: number;
  program: string;
  name: string;
  type: "all_of" | "one_of" | "n_of" | "category_credits" | "credits";
  courses: string[];
  category: string | null;
  credits_required: number;
  count_required: number;
  display_order: number;
  notes: string;
}

export interface Student {
  id: number;
  name: string;
  school: string;
  major: string;
  minor: string | null;
  current_term: string;
  graduation_term: string;
  completed_courses: string[];
  transfer_credits: { code?: string; category?: string; credits: number }[];
  preferred_workload: number;
  max_credits_per_term: number;
  career_goals: string[];
  constraints: Record<string, unknown>;
  programs: string[];
  created_at?: string;
}

export type StudentCreate = Omit<Student, "id" | "created_at">;

export interface RequirementProgress {
  requirement_id: number;
  name: string;
  type: string;
  satisfied: boolean;
  progress_pct: number;
  completed_courses: string[];
  missing_courses: string[];
  needed_credits: number;
  earned_credits: number;
  notes: string;
}

export interface AuditReport {
  student_id: number;
  program: string;
  requirements: RequirementProgress[];
  total_credits_completed: number;
  total_credits_required: number;
  overall_progress_pct: number;
  completed_count: number;
  total_count: number;
  blockers: string[];
  warnings: string[];
}

export interface SemesterPlan {
  term: string;
  courses: string[];
  total_credits: number;
  workload_score: number;
}

export interface PlanWarning {
  severity: "info" | "warning" | "error";
  code: string;
  message: string;
  term?: string | null;
  course?: string | null;
}

export interface Plan {
  id?: number | null;
  student_id: number;
  name: string;
  strategy: string;
  terms: SemesterPlan[];
  warnings: PlanWarning[];
  summary: Record<string, any>;
  created_at?: string | null;
}

export interface PlanCompareResult {
  plans: Plan[];
  summaries: Record<string, any>[];
  winner: string | null;
  rationale: string;
  audits: AuditReport[];
}

export interface AdvisorToolCall {
  tool: string;
  inputs: Record<string, any>;
  output: Record<string, any>;
}

export interface AdvisorResponse {
  intent: string;
  answer: string;
  tool_calls: AdvisorToolCall[];
  citations: string[];
  suggestions: string[];
}

export interface AgentTrace {
  agent: string;          // "Orchestrator" | "Researcher" | "Planner" | "Critic" | "Explainer"
  action: string;
  status: string;         // "ok" | "retry" | "rejected" | "error"
  summary: string;
  duration_ms: number;
}

export interface CriticViolation {
  code: string;
  message: string;
  severity: string;
}

export interface AdvisorV2Response extends AdvisorResponse {
  agent_trace: AgentTrace[];
  retry_count: number;
  critic_violations: CriticViolation[];
}
