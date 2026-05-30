/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: "#090A0F",
          800: "#121420",
          700: "#1E2235",
          600: "#2B314B",
          500: "#444E72",
        },
        primary: {
          light: "#7928CA",
          DEFAULT: "#581C87",
          dark: "#3B0764",
        },
        accent: {
          cyan: "#00DF89",
          magenta: "#FF007A",
          violet: "#8B5CF6",
        }
      },
      fontFamily: {
        sans: ["Outfit", "Inter", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
        "glass-inset": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.1)",
      }
    },
  },
  plugins: [],
}
