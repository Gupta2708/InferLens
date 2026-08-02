"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AppNav } from "@/components/layout/app-nav";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/") return <>{children}</>;
  return <>
    <header className="sticky top-0 z-30 border-b border-black/10 bg-paper/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <Link href="/" className="brand-link group" aria-label="InferLens home">
          <span className="logo-mark-shell"><Image src="/inferlens-mark.svg" alt="" width={44} height={44} className="logo-mark-image" priority /></span>
          <span className="brand-title">Infer<span>Lens</span></span>
        </Link>
        <AppNav />
      </div>
    </header>
    {children}
  </>;
}
