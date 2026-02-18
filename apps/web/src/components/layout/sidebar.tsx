"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const links = [
  ["/dashboard", "Dashboard"],
  ["/jobs", "Jobs Inbox"],
  ["/followups", "Follow-ups"],
  ["/feed", "Feed Hunter"],
] as const;

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-64 border-r border-border bg-card p-4">
      <h1 className="mb-6 text-lg font-semibold">job-agent-arkode</h1>
      <nav className="space-y-2">
        {links.map(([href, label]) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "block rounded-md px-3 py-2 text-sm",
              pathname.startsWith(href) ? "bg-primary text-white" : "text-muted hover:bg-zinc-900",
            )}
          >
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
