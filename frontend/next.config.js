/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    let api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    if (!api.startsWith("http://") && !api.startsWith("https://")) {
      api = `https://${api}`;
    }
    return [{ source: "/api/v1/:path*", destination: `${api}/api/v1/:path*` }];
  },
};


module.exports = nextConfig;
