/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#060A13", 900: "#0A101D", 850: "#0E1526", 800: "#121A2E", 700: "#1B2540", 600: "#283456" },
        electric: { 300: "#8CC4FF", 400: "#5AA9FF", 500: "#2F81F7", 600: "#1F6FE0" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "ui-monospace", "monospace"] },
    },
  },
  plugins: [],
};
