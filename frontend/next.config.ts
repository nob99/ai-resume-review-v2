import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  eslint: {
    // Skip ESLint during production builds (deploy will handle linting separately)
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Skip TypeScript type checking during production builds (CI will handle type checking)
    ignoreBuildErrors: true,
  },
  // Environment variable for API URL
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
};

export default nextConfig;
