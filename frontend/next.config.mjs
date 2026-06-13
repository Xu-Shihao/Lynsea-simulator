/** @type {import('next').NextConfig} */
// Backend origin is configurable for local dev; defaults to the contract's :8000.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || 'http://localhost:8000';
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_ORIGIN}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
