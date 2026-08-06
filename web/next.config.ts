import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/action/:pin",
        destination: "/?pin=:pin#result",
        permanent: true,
      },
      {
        source: "/district/:name",
        destination: "/?district=:name#result",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
