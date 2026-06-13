import type { NextConfig } from "next";

// GitHub Pages serves a project site under /<repo>/, and can only host static
// files. We gate the static-export settings on env vars so local `npm run dev`
// (and a local live backend) keep working at the root path unchanged:
//   GITHUB_PAGES=true         → emit a static export under the repo basePath
//   NEXT_PUBLIC_STATIC_DEMO=1 → the UI knows there is no backend (demo only)
const isPages = process.env.GITHUB_PAGES === "true";
const repoBasePath = "/Lynsea-simulator";

const nextConfig: NextConfig = {
  // Static HTML export — required for GitHub Pages (no Node server there).
  output: "export",
  // Emit `route/index.html` so GitHub Pages serves clean URLs without 404s.
  trailingSlash: true,
  // The export target has no Image Optimization server.
  images: { unoptimized: true },
  // Only prefix assets/routes when building for GitHub Pages.
  ...(isPages ? { basePath: repoBasePath, assetPrefix: `${repoBasePath}/` } : {}),
};

export default nextConfig;
