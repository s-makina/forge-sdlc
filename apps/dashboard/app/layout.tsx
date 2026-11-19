import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "ForgeSDLC",
  description: "Autonomous SDLC Platform",
};

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/projects", label: "Projects" },
  { href: "/agents", label: "Agents" },
  { href: "/models", label: "Models" },
  { href: "/workflows", label: "Workflows" },
  { href: "/tasks", label: "Tasks" },
  { href: "/executions", label: "Executions" },
  { href: "/approvals", label: "Approvals" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/evaluations", label: "Evaluations" },
  { href: "/reports", label: "Reports" },
  { href: "/settings", label: "Settings" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link href="/" className="brand">
            ForgeSDLC
          </Link>
          <nav>
            {NAV_ITEMS.map((item) => (
              <Link key={item.href} href={item.href} className="nav-link">
                {item.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="content">{children}</main>
      </body>
    </html>
  );
}
