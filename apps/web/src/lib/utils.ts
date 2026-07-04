import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const formatPct = (n: number) => `${Math.round(n * 100)}%`;

export const titleCase = (s: string) =>
  s.replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const workloadLabel = (level: number) => {
  if (level <= 1) return "Light";
  if (level === 2) return "Moderate";
  if (level === 3) return "Normal";
  if (level === 4) return "Heavy";
  return "Brutal";
};
