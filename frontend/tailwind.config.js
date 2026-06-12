/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: '#1a1f36',
        accent: '#38c77e',
      },
    },
  },
  plugins: [],
};
