import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // Docker optimization
  experimental: {
    outputFileTracingRoot: undefined,
  },
  // Environment variable for API URL
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
};

export default nextConfig;
