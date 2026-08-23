"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export function NavLink({ href, label, icon }: { href: string; label: string; icon: ReactNode }) {
  const pathname = usePathname();
  const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
  return <Link className={`nav-item${active ? " active" : ""}`} href={href} aria-current={active ? "page" : undefined}>{icon}<span>{label}</span></Link>;
}
