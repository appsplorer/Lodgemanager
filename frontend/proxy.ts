import {NextRequest,NextResponse} from 'next/server';

export function proxy(request:NextRequest){
 const nonce=btoa(crypto.randomUUID()).replace(/=+$/,'');
 const csp=[
  "default-src 'self'",
  `script-src 'self' 'nonce-${nonce}' 'strict-dynamic' https:`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "connect-src 'self' https://www.google-analytics.com https://analytics.google.com https://www.facebook.com",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "upgrade-insecure-requests",
 ].join('; ');
 const headers=new Headers(request.headers);headers.set('x-nonce',nonce);headers.set('Content-Security-Policy',csp);
 const response=NextResponse.next({request:{headers}});response.headers.set('Content-Security-Policy',csp);response.headers.set('X-Content-Type-Options','nosniff');response.headers.set('Referrer-Policy','strict-origin-when-cross-origin');response.headers.set('Permissions-Policy','camera=(), microphone=(), geolocation=(), payment=(self)');return response;
}

export const config={matcher:["/((?!api|_next/static|_next/image|favicon.ico|sw.js|manifest.webmanifest).*)"]};
