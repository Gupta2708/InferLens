"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { ActivityIcon, CompareIcon, DatabaseIcon, MessageIcon, PlugIcon } from "@/components/ui/icons";
import { ThemeToggle } from "@/components/layout/theme-toggle";

const nav = [
  { label: "Chat", href: "/chat", icon: MessageIcon },
  { label: "Dashboard", href: "/dashboard", icon: ActivityIcon },
  { label: "Logs & Traces", href: "/logs", icon: DatabaseIcon },
  { label: "Comparisons", href: "/comparisons", icon: CompareIcon },
  { label: "Providers", href: "/settings/providers", icon: PlugIcon }
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <div className="flex flex-wrap items-center gap-2">
      <nav className="flex flex-wrap items-center gap-1 text-sm">
        {nav.map(({ label, href, icon: Icon }) => {
          const active = pathname === href || (href === "/logs" && pathname.startsWith("/traces")) || (href !== "/chat" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              className={clsx(
                "nav-link group",
                active
                  ? "nav-link-active border-signal/35 bg-card text-ink"
                  : "border-transparent text-ink/65 hover:border-black/10 hover:bg-card/80 hover:text-ink"
              )}
              href={href}
            >
              <Icon className={clsx("h-4 w-4 transition-colors", active ? "text-signal" : "text-ink/45 group-hover:text-signal")} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
      <ThemeToggle />
    </div>
  );
}
