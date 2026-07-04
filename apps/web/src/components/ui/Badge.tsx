import { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type Variant = "default" | "accent" | "ok" | "warn" | "danger";

export function Badge({
  variant = "default",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  const map: Record<Variant, string> = {
    default: "badge",
    accent: "badge-accent",
    ok: "badge-ok",
    warn: "badge-warn",
    danger: "badge-danger",
  };
  return <span className={cn(map[variant], className)} {...props} />;
}
