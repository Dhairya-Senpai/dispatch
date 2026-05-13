"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Mail, Users, BarChart2, Settings, Zap } from "lucide-react";
import { clsx } from "clsx";

const nav = [
  { href: "/dashboard",  label: "Dashboard",  icon: LayoutDashboard },
  { href: "/campaigns",  label: "Campaigns",  icon: Mail },
  { href: "/contacts",   label: "Contacts",   icon: Users },
  { href: "/analytics",  label: "Analytics",  icon: BarChart2 },
  { href: "/settings",   label: "Settings",   icon: Settings },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-gray-100">
        <div className="bg-indigo-600 text-white rounded-lg p-1.5">
          <Zap size={16} />
        </div>
        <span className="font-semibold text-gray-900 text-lg tracking-tight">Dispatch</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              path.startsWith(href)
                ? "bg-indigo-50 text-indigo-700"
                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-gray-100">
        <p className="text-xs text-gray-400">Dispatch v0.1.0</p>
      </div>
    </aside>
  );
}
