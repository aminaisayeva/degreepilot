import type {
  AdvisorResponse,
  AdvisorV2Response,
  AuditReport,
  Course,
  Plan,
  PlanCompareResult,
  Requirement,
  Student,
  StudentCreate,
} from "@/types/api";

const RAW_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";
const API_BASE = RAW_BASE.replace(/\/+$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listCourses: (params?: {
    q?: string;
    category?: string;
    career_tag?: string;
    term?: string;
  }) => {
    const search = new URLSearchParams();
    if (params?.q) search.set("q", params.q);
    if (params?.category) search.set("category", params.category);
    if (params?.career_tag) search.set("career_tag", params.career_tag);
    if (params?.term) search.set("term", params.term);
    const qs = search.toString();
    return request<Course[]>(`/courses${qs ? `?${qs}` : ""}`);
  },
  getCourse: (code: string) => request<Course>(`/courses/${code}`),
  listPrograms: () => request<{ slug: string; label: string }[]>(`/requirements`),
  getRequirements: (program: string) => request<Requirement[]>(`/requirements/${program}`),
  listStudents: () => request<Student[]>(`/students`),
  getStudent: (id: number) => request<Student>(`/students/${id}`),
  createStudent: (body: StudentCreate) =>
    request<Student>(`/students`, { method: "POST", body: JSON.stringify(body) }),
  updateStudent: (id: number, body: StudentCreate) =>
    request<Student>(`/students/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  getAudit: (id: number, program = "columbia_cs_major") =>
    request<AuditReport>(`/students/${id}/audit?program=${program}`),
  generatePlans: (student_id: number, strategies: string[]) =>
    request<Plan[]>(`/plans/generate`, {
      method: "POST",
      body: JSON.stringify({ student_id, strategies }),
    }),
  validatePlan: (student_id: number, plan: Plan) =>
    request<{ is_valid: boolean; warnings: Plan["warnings"] }>(`/plans/validate`, {
      method: "POST",
      body: JSON.stringify({ student_id, plan }),
    }),
  comparePlans: (student_id: number, plans: Plan[]) =>
    request<PlanCompareResult>(`/plans/compare`, {
      method: "POST",
      body: JSON.stringify({ student_id, plans }),
    }),
  chat: (student_id: number, message: string, plan_id?: number | null) =>
    request<AdvisorResponse>(`/advisor/chat`, {
      method: "POST",
      body: JSON.stringify({ student_id, message, plan_id: plan_id ?? null }),
    }),
  chatV2: (student_id: number, message: string, plan_id?: number | null) =>
    request<AdvisorV2Response>(`/advisor/v2/chat`, {
      method: "POST",
      body: JSON.stringify({ student_id, message, plan_id: plan_id ?? null }),
    }),
};
