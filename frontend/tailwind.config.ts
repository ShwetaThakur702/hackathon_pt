import type { Config } from "tailwindcss";

// Centralized design tokens — Paytm-inspired fintech blue/cyan direction,
// original values, no proprietary assets. Components should reference
// these semantic names (brand/success/warning/danger/ink/...) rather than
// arbitrary Tailwind colors, so the palette stays consistent everywhere.
const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          DEFAULT: "#00B9F1",
          dark: "#002970",
          navy: "#001B44",
          cyan: "#00BAF2",
          light: "#E8F8FD",
        },
        success: { DEFAULT: "#00A86B", light: "#E4F7EF" },
        warning: { DEFAULT: "#F59E0B", light: "#FEF3E2" },
        danger: { DEFAULT: "#E53935", light: "#FDECEC" },
        ink: {
          DEFAULT: "#1F2937",
          secondary: "#6B7280",
        },
        surface: "#F5F7FA",
        border: "#E5E7EB",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 3px 0 rgb(0 0 0 / 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
