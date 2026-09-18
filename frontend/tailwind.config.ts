/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0e14",
        panel: "#0f141d",
        panel2: "#131a25",
        border: "#1e2733",
        muted: "#8a97a8",
        accent: "#3b82f6",
        accent2: "#22d3ee",
        ok: "#22c55e",
        warn: "#f59e0b",
        danger: "#ef4444",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Inter", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      keyframes: {
        fadeIn: { "0%": { opacity: "0", transform: "translateY(4px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        pulse2: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.4" } },
      },
      animation: { fadeIn: "fadeIn .4s ease-out", pulse2: "pulse2 1.6s ease-in-out infinite" },
    },
  },
  plugins: [],
};
