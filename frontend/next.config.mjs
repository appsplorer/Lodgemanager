/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  compress: true,
  async rewrites() {
    return [{ source: '/api/:path*', destination: 'http://backend:8000/api/:path*' }];
  },
  async headers() {
    return [
      { source: '/sw.js', headers: [
        { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
        { key: 'Service-Worker-Allowed', value: '/' },
      ]},
      { source: '/manifest.webmanifest', headers: [{ key: 'Cache-Control', value: 'public, max-age=3600' }]},
      { source: '/:path*', headers: [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
      ]},
    ];
  },
};
export default nextConfig;
