import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  allowedDevOrigins: ["100.103.253.75"],
  images: {
    unoptimized: true
  }
};

export default nextConfig;
