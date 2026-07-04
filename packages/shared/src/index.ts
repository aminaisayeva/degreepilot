// Shared TypeScript types — mirror of `apps/api/app/schemas`.
// The frontend ships its own copy under `apps/web/src/types/api.ts` for
// zero-friction local dev. Keep this file in sync when API schemas change.

export type Severity = "info" | "warning" | "error";

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

export interface SemesterPlan {
  term: string;
  courses: string[];
  total_credits: number;
  workload_score: number;
}

export interface PlanWarning {
  severity: Severity;
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
  summary: Record<string, unknown>;
}
