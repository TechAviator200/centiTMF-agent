/** @type {import('next').NextConfig} */

// In production (Vercel), set NEXT_PUBLIC_API_URL to your Render backend URL,
// e.g. https://centitmf-backend.onrender.com
// INTERNAL_API_URL is used for server-side (SSR) fetches from Vercel edge to Render.
// In Docker dev, both default to the backend container / localhost.
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const INTERNAL_BACKEND_URL = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${INTERNAL_BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
