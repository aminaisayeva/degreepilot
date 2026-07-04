import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1280px" },
    },
    extend: {
      colors: {
        bg: "hsl(220 25% 7%)",
        surface: "hsl(220 22% 10%)",
        elevated: "hsl(220 18% 14%)",
        border: "hsl(220 14% 22%)",
        muted: "hsl(220 10% 60%)",
        ink: "hsl(220 20% 96%)",
        accent: {
          DEFAULT: "hsl(196 96% 56%)",
          ink: "hsl(220 25% 7%)",
        },
        ok: "hsl(150 70% 48%)",
        warn: "hsl(38 95% 60%)",
        danger: "hsl(0 80% 62%)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 rgba(255,255,255,0.04), 0 6px 24px rgba(0,0,0,0.35)",
        glow: "0 0 0 1px hsl(196 96% 56% / 0.35), 0 0 24px hsl(196 96% 56% / 0.25)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
