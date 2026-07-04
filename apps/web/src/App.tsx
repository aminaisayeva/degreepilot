import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { AdvisorPage } from "@/features/chat/AdvisorPage";
import { ComparePage } from "@/features/compare/ComparePage";
import { CoursesPage } from "@/features/courses/CoursesPage";
import { GraphPage } from "@/features/graph/GraphPage";
import { LandingPage } from "@/features/landing/LandingPage";
import { OnboardingPage } from "@/features/onboarding/OnboardingPage";
import { DashboardPage } from "@/features/audit/DashboardPage";
import { PlannerPage } from "@/features/planner/PlannerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/planner" element={<PlannerPage />} />
        <Route path="/courses" element={<CoursesPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/advisor" element={<AdvisorPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
