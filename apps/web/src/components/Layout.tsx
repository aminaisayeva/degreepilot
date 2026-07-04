import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  BookOpen,
  CalendarDays,
  GitBranch,
  LayoutDashboard,
  MessageSquare,
  ScaleIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/planner", label: "Planner", icon: CalendarDays },
  { to: "/courses", label: "Courses", icon: BookOpen },
  { to: "/graph", label: "Prereq graph", icon: GitBranch },
  { to: "/advisor", label: "Advisor", icon: MessageSquare },
  { to: "/compare", label: "Compare", icon: ScaleIcon },
];

export function Layout() {
  const location = useLocation();
  const hideShell = location.pathname === "/" || location.pathname === "/onboarding";

  if (hideShell) {
    return <Outlet />;
  }

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 border-r border-border bg-surface/60 px-4 py-6 md:flex md:flex-col">
        <NavLink to="/" className="mb-8 flex items-center gap-2 px-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-accent/15 text-accent">
            <Activity className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-bold tracking-tight">DegreePilot</div>
            <div className="text-[10px] text-muted">Plans that validate.</div>
          </div>
        </NavLink>

        <nav className="space-y-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition",
                  isActive
                    ? "bg-elevated text-ink"
                    : "text-muted hover:bg-elevated/60 hover:text-ink",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto rounded-xl border border-dashed border-border bg-surface p-3 text-xs text-muted">
          Sample data. Not an official catalog.
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
