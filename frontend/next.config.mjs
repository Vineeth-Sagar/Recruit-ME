/** @type {import('next').NextConfig} */
const API_TARGET = process.env.API_PROXY_TARGET || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    // Same-origin proxy so the httpOnly refresh cookie is scoped to the web app.
    return [{ source: "/api/:path*", destination: `${API_TARGET}/api/:path*` }];
  },
};

export default nextConfig;
