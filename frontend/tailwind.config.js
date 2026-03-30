/** @type {import('tailwindcss').Config} */
export default {
  // darkMode: 'class' — le varianti dark: richiedono .dark sul root; non la applichiamo mai (solo tema chiaro).
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
