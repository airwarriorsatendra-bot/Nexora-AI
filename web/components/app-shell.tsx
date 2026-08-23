import Link from "next/link";
import {
  Activity,
  BarChart3,
  Bot,
  ChartNoAxesCombined,
  ChevronDown,
  Gauge,
  Link2,
  MapPin,
  Megaphone,
  Search,
  Send,
  Settings,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";

import { BrandMark } from "@/components/brand-mark";
import { NavLink } from "@/components/nav-link";

const navigation = [
  {
    label: "Workspace",
    items: [
      { label: "Overview", icon: Gauge, href: "/" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { label: "SEO Intelligence", icon: Search, href: "/seo" },
      { label: "AI Visibility", icon: Sparkles, href: "/ai-visibility" },
      { label: "AEO & GEO", icon: Bot, href: "/seo/aeo-geo" },
      { label: "Backlinks", icon: Link2, href: "/backlinks" },
      { label: "Local SEO", icon: MapPin, href: "/local-seo" },
    ],
  },
  {
    label: "Activation",
    items: [
      { label: "Outreach", icon: Send, href: "/outreach" },
      { label: "Google Ads", icon: Megaphone, href: "/google-ads" },
      { label: "Meta Ads", icon: Activity, href: "/meta-ads" },
      { label: "Analytics", icon: BarChart3, href: "/analytics" },
    ],
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="Nexora AI home">
          <BrandMark />
          <span>
            <strong>Nexora AI</strong>
            <small>Intelligence OS</small>
          </span>
        </Link>
        <nav className="nav" aria-label="Primary navigation">
          {navigation.map((group) => (
            <section className="nav-group" key={group.label}>
              <p>{group.label}</p>
              {group.items.map((item) => (
                <NavLink
                  key={item.label}
                  href={item.href}
                  label={item.label}
                  icon={<item.icon size={17} strokeWidth={1.8} />}
                />
              ))}
            </section>
          ))}
        </nav>
        <div className="sidebar-footer">
          <Link href="/settings"><Settings size={17} /> Settings</Link>
          <div className="workspace-switcher">
            <span className="avatar">ND</span>
            <span><strong>Nexora Digital</strong><small>Beta workspace</small></span>
            <ChevronDown size={15} />
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="global-search">
            <Search size={17} />
            <span>Search workspace</span>
            <kbd>⌘ K</kbd>
          </div>
          <div className="topbar-actions">
            <span className="status-pill"><i /> Systems operational</span>
            <Link className="icon-button" href="/analytics" aria-label="Open analytics"><ChartNoAxesCombined size={18} /></Link>
            <span className="avatar compact">ND</span>
          </div>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
