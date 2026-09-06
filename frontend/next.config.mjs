/** @type {import('next').NextConfig} */
const API_TARGET = process.env.API_PROXY_TARGET || "http://localhost:8000";

const nextConfig = {
  // Emit a self-contained server bundle (.next/standalone) for a lean image.
  output: "standalone",
  async rewrites() {
    // Same-origin proxy so the httpOnly refresh cookie is scoped to the web app.
    // `rewrites()` is re-evaluated when the standalone server boots, so
    // API_PROXY_TARGET can be set at container runtime.
    return [{ source: "/api/:path*", destination: `${API_TARGET}/api/:path*` }];
  },
};

export default nextConfig;
