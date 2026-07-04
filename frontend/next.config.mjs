/** @type {import('next').NextConfig} */

// The API's JSON-response CSP (`default-src 'self'` and nothing else) does not
// work for this HTML app: every component uses inline `style={{ ... }}` (the
// established convention here, backed by CSS custom properties per CLAUDE.md
// §6), fonts load from Google Fonts, and the browser fetches a cross-origin
// backend. A bare `default-src 'self'` silently breaks all of that — verified
// by loading the app in a real browser with these headers active, not just
// `next build`, which doesn't execute the page and can't catch this.
const backendOrigin = (() => {
  try {
    return new URL(process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000").origin;
  } catch {
    return "http://localhost:8000";
  }
})();

const isDev = process.env.NODE_ENV !== "production";

const csp = [
  "default-src 'self'",
  // 'unsafe-inline' is required for the inline style={{}} pattern used throughout
  // the app; 'unsafe-eval' is only needed for Next.js dev-mode Fast Refresh.
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  // blob: is required for the click-to-load attachment viewer (AttachmentViewer.tsx),
  // which renders images/video from an in-memory object URL created from a fetched
  // blob -- never a remote URL, so this doesn't open the door to loading remote media.
  "img-src 'self' data: blob:",
  "media-src 'self' blob:",
  `connect-src 'self' ${backendOrigin}`,
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
].join("; ");

const nextConfig = {
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "no-referrer" },
          {
            key: "Content-Security-Policy",
            value: csp,
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
