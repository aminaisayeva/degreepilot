import { cn } from "@/lib/utils";

export function Progress({ value, className }: { value: number; className?: string }) {
  const v = Math.max(0, Math.min(1, value));
  return (
    <div className={cn("progress-track", className)} aria-valuenow={Math.round(v * 100)}>
      <div className="progress-fill" style={{ width: `${v * 100}%` }} />
    </div>
  );
}
