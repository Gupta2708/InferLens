import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { AppNav } from "@/components/layout/app-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "InferLens",
  description: "LLM gateway and inference observability platform",
  icons: {
    icon: "/inferlens-mark.svg",
    apple: "/inferlens-mark.svg"
  }
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(()=>{try{const t=localStorage.getItem('infersight-theme')||'dark';document.documentElement.classList.toggle('dark',t==='dark');document.documentElement.dataset.theme=t;}catch(e){document.documentElement.classList.add('dark');document.documentElement.dataset.theme='dark';}})();"
          }}
        />
      </head>
      <body>
        <div className="min-h-screen">
          <header className="sticky top-0 z-30 border-b border-black/10 bg-paper/90 backdrop-blur">
            <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <Link href="/chat" className="brand-link group">
                <span className="logo-wordmark-shell">
                  <Image src="/inferlens-logo.svg" alt="InferLens" width={184} height={56} className="logo-wordmark-image" priority />
                </span>
                <span className="sm:hidden text-base font-semibold">InferLens</span>
              </Link>
              <AppNav />
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
