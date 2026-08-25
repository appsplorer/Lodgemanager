import './globals.css';import type {Metadata,Viewport} from 'next';import type {ReactNode} from 'react';
export const metadata:Metadata={title:{default:'LodgeFlow',template:'%s · LodgeFlow'},description:'Private lodge administration',manifest:'/manifest.webmanifest'};
export const viewport:Viewport={themeColor:'#102a43',width:'device-width',initialScale:1};
export default function RootLayout({children}:{children:ReactNode}){return <html lang="en"><body>{children}</body></html>}
