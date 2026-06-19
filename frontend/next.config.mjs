const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "geolocation=(), camera=(), microphone=()" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://checkout.razorpay.com",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https://*.supabase.co",
              "media-src 'self' blob: https://*.supabase.co",
              "font-src 'self'",
              `connect-src 'self' ${apiUrl} https://*.supabase.co https://api.razorpay.com wss://*.supabase.co`,
              "frame-src https://api.razorpay.com",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
