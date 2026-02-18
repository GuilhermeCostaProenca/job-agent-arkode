import { ButtonHTMLAttributes, PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

type Props = PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>> & {
  variant?: "default" | "outline" | "ghost" | "destructive";
};

export function Button({ className, variant = "default", children, ...props }: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center rounded-md px-3 py-2 text-sm font-medium transition",
        variant === "default" && "bg-primary text-white hover:opacity-90",
        variant === "outline" && "border border-border bg-transparent hover:bg-card",
        variant === "ghost" && "hover:bg-card",
        variant === "destructive" && "bg-red-600 text-white hover:opacity-90",
        props.disabled && "cursor-not-allowed opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
