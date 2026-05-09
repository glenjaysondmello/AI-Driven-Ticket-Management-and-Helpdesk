"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * TopBar — persistent navigation strip across all pages.
 * Uses the `active` CSS class to highlight the current route.
 */
export default function TopBar() {
  const pathname = usePathname();

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <div className="topbar-dot" aria-hidden="true" />
        <span>AI&nbsp;Helpdesk</span>
      </div>
      <nav className="topbar-nav" aria-label="Main navigation">
        <Link
          href="/"
          className={pathname === "/" ? "active" : ""}
          aria-current={pathname === "/" ? "page" : undefined}
        >
          Chat
        </Link>
        <Link
          href="/dashboard"
          className={pathname.startsWith("/dashboard") ? "active" : ""}
          aria-current={pathname.startsWith("/dashboard") ? "page" : undefined}
        >
          Dashboard
        </Link>
      </nav>
    </header>
  );
}
