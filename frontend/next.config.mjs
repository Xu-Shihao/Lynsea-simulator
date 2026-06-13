/** @type {import('next').NextConfig} */
const nextConfig = {
  // Backend API is at http://localhost:8000
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
