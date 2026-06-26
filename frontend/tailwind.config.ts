import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        "bg-soft": "var(--color-bg-soft)",
        surface: "var(--color-surface)",
        "surface-raised": "var(--color-surface-raised)",
        navy: "var(--color-navy)",
        "navy-soft": "var(--color-navy-soft)",
        "navy-muted": "var(--color-navy-muted)",
        text: "var(--color-text)",
        "text-soft": "var(--color-text-soft)",
        "text-muted": "var(--color-text-muted)",
        "text-on-dark": "var(--color-text-on-dark)",
        border: "var(--color-border)",
        "border-strong": "var(--color-border-strong)",
        gold: "var(--color-gold)",
        "gold-soft": "var(--color-gold-soft)",
        "gold-faint": "var(--color-gold-faint)",
        sage: "var(--color-sage)",
        clay: "var(--color-clay)",
        cream: "var(--color-cream)",
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        info: "var(--color-info)",
      },
      fontFamily: {
        display: ["var(--font-display)"],
        ui: ["var(--font-ui)"],
        mono: ["var(--font-mono)"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
    },
  },
  plugins: [],
};
export default config;
