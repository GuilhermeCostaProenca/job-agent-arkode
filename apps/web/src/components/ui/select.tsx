import { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(
        "h-10 w-full rounded-md border border-border bg-zinc-950 px-3 text-sm outline-none focus:ring-2 focus:ring-primary",
        props.className,
      )}
    />
  );
}
