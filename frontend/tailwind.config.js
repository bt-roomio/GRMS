import colors from "./tailwind.colors.js";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{vue,scss,css,js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: colors
    },
    plugins: [],
  }
}

