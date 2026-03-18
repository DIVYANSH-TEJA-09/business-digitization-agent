import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Ignore ESLint errors on Vercel so it successfully builds our MVP code
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
