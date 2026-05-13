"use client";

import { BarChart2 } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Analytics</h1>
      <div className="text-center py-20 text-gray-400">
        <BarChart2 size={40} className="mx-auto mb-3 opacity-30" />
        <p>Analytics dashboard coming soon.</p>
      </div>
    </div>
  );
}
