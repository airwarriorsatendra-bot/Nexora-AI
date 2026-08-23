import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: { default: "Nexora AI", template: "%s · Nexora AI" },
  description: "Enterprise marketing intelligence powered by Nexora Digital Hub.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><AppShell>{children}</AppShell></body>
    </html>
  );
}
