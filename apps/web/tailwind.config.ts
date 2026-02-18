import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "#09090b",
        foreground: "#fafafa",
        card: "#111113",
        border: "#27272a",
        muted: "#a1a1aa",
        primary: "#5b8cff"
      }
    }
  },
  plugins: []
};

export default config;
