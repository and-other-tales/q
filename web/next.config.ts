// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  
  // API rewrite for development and standalone mode
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/:path*`,
      },
    ];
  },
  
  // Enable compression
  compress: true,
  
  // Power-off source maps in production for better performance
  productionBrowserSourceMaps: false,
  
  // Optimize images
  images: {
    domains: ['localhost'],
    formats: ['image/webp', 'image/avif'],
  },
  
  // Experimental features for better performance
  experimental: {
    optimizeCss: true,
  },
};

export default nextConfig;
