/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        titan: {
          bg: "#000000",
          sidebar: "#000000",
          input: "#1E1E1E",
          hover: "#141414",
          selected: "#1C1C1C",
          border: "#262626",
          text: "#F5F5F5",
          muted: "#A3A3A3",
          subtle: "#737373",
          accent: "#3B82F6",
          success: "#22C55E",
          warning: "#F59E0B",
          error: "#EF4444"
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
