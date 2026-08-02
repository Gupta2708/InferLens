     import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "InferLens — LLM Gateway and Observability Platform",
  description: "Route, trace, replay, and compare LLM requests across providers with latency, token, cost, error, and lifecycle observability.",
  openGraph: { title: "InferLens — LLM Gateway and Observability Platform", description: "Route, trace, replay, and compare LLM requests across providers with latency, token, cost, error, and lifecycle observability." },
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
        <div className="min-h-screen"><AppShell>{children}</AppShell></div>
      </body>
    </html>
  );
}
