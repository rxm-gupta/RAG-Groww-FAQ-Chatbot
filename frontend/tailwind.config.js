/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        groww: {
          green: "#00b386",
          dark: "#1f2937",
        },
      },
    },
  },
  plugins: [],
};
