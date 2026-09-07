/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained server bundle (.next/standalone) for a lean image.
  output: "standalone",
  // The /api/* proxy is a runtime route handler (src/app/api/[...path]/route.ts),
  // not a rewrite, so API_PROXY_TARGET is honoured at container runtime.
};

export default nextConfig;
