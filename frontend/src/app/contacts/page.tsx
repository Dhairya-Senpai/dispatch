"use client";

import { Users } from "lucide-react";

export default function ContactsPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Contacts</h1>
      <div className="text-center py-20 text-gray-400">
        <Users size={40} className="mx-auto mb-3 opacity-30" />
        <p>Contacts management coming soon.</p>
      </div>
    </div>
  );
}
