/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0f1d",
        surface: "#121829",
        surfaceLight: "#1a2236",
        surfaceBorder: "rgba(255, 255, 255, 0.08)",
        accentBlue: "#00d2ff",
        accentCyan: "#00f5d4",
        accentViolet: "#7928ca",
        accentOrange: "#ff9900",
        accentRed: "#ff3366",
        accentGreen: "#00ff88"
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"]
      }
    },
  },
  plugins: [],
}
