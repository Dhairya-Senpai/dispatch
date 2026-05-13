"use client";

import { Settings } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Settings</h1>
      <div className="text-center py-20 text-gray-400">
        <Settings size={40} className="mx-auto mb-3 opacity-30" />
        <p>Settings coming soon.</p>
      </div>
    </div>
  );
}
