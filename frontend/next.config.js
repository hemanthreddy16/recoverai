/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    let api =
      process.env.API_URL ||
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.INTERNAL_API_URL ||
      "http://localhost:8000";

    api = api.trim().replace(/\/+$/, "");
    if (!api.startsWith("http://") && !api.startsWith("https://")) {
      if (api.includes("localhost") || api.includes("127.0.0.1") || !api.includes(".")) {
        api = `http://${api}`;
      } else {
        api = `https://${api}`;
      }
    }

    return [
      { source: "/api/v1/:path*", destination: `${api}/api/v1/:path*` },
      { source: "/backend-health", destination: `${api}/health` },
    ];
  },
};

module.exports = nextConfig;
