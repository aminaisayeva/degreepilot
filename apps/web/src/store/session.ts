import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Plan } from "@/types/api";

interface SessionState {
  studentId: number | null;
  setStudentId: (id: number | null) => void;
  activePlanIndex: number;
  setActivePlanIndex: (i: number) => void;
  plans: Plan[];
  setPlans: (plans: Plan[]) => void;
}

export const useSession = create<SessionState>()(
  persist(
    (set) => ({
      studentId: null,
      // Switching students invalidates any plans generated for the previous one.
      setStudentId: (studentId) =>
        set((prev) =>
          prev.studentId === studentId
            ? { studentId }
            : { studentId, plans: [], activePlanIndex: 0 },
        ),
      activePlanIndex: 0,
      setActivePlanIndex: (activePlanIndex) => set({ activePlanIndex }),
      plans: [],
      setPlans: (plans) => set({ plans, activePlanIndex: 0 }),
    }),
    { name: "degreepilot-session" },
  ),
);
