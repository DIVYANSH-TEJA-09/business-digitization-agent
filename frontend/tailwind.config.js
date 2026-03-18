/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#FDFBF7',  // Cream
        foreground: '#3D2B1F',  // Dark brown
        primary: {
          DEFAULT: '#C4795D',   // Terracotta
          foreground: '#FFFFFF',
        },
        secondary: {
          DEFAULT: '#8FA895',   // Sage green
          foreground: '#FFFFFF',
        },
        muted: {
          DEFAULT: '#E8E4DC',   // Light beige
          foreground: '#6B5B4F', // Medium brown
        },
        accent: {
          DEFAULT: '#D4A574',   // Warm tan
          foreground: '#3D2B1F',
        },
        card: {
          DEFAULT: '#FFFFFF',
          foreground: '#3D2B1F',
        },
      },
      borderRadius: {
        lg: '0.5rem',
        md: 'calc(0.5rem - 2px)',
        sm: 'calc(0.5rem - 4px)',
      },
    },
  },
  plugins: [],
}
