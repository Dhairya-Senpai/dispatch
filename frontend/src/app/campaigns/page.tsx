"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { campaignApi, type Campaign } from "@/lib/api";
import { Plus, Send, Sparkles, Eye } from "lucide-react";
import Link from "next/link";

const STATUS_COLORS: Record<Campaign["status"], string> = {
  draft:     "bg-gray-100 text-gray-600",
  sending:   "bg-yellow-100 text-yellow-700",
  sent:      "bg-green-100 text-green-700",
  scheduled: "bg-blue-100 text-blue-700",
};

export default function CampaignsPage() {
  const qc = useQueryClient();
  const { data: campaigns = [], isLoading } = useQuery({
    queryKey: ["campaigns"],
    queryFn:  campaignApi.list,
  });

  const sendMutation = useMutation({
    mutationFn: (id: string) => campaignApi.send(id),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  if (isLoading) {
    return <div className="p-8 text-gray-400">Loading campaigns…</div>;
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Campaigns</h1>
        <Link
          href="/campaigns/new"
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} /> New Campaign
        </Link>
      </div>

      {campaigns.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Mail size={40} className="mx-auto mb-3 opacity-30" />
          <p>No campaigns yet. Create your first one.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {campaigns.map((c) => (
            <div key={c.campaignId} className="flex items-center justify-between p-4">
              <div>
                <p className="font-medium text-gray-900">{c.name}</p>
                <p className="text-sm text-gray-500 mt-0.5">{c.subject}</p>
              </div>
              <div className="flex items-center gap-4">
                {c.status === "sent" && (
                  <div className="flex gap-4 text-sm text-gray-500">
                    <span><Eye size={13} className="inline mr-1" />{c.openCount ?? 0}</span>
                    <span><MousePointerClick size={13} className="inline mr-1" />{c.clickCount ?? 0}</span>
                  </div>
                )}
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_COLORS[c.status]}`}>
                  {c.status}
                </span>
                {c.status === "draft" && (
                  <button
                    onClick={() => sendMutation.mutate(c.campaignId)}
                    disabled={sendMutation.isPending}
                    className="flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                  >
                    <Send size={14} /> Send
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Mail(props: any) {
  return <svg {...props} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>;
}

function MousePointerClick(props: any) {
  return <svg {...props} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 9 5 12 1.8-5.2L21 14Z"/><path d="M7.2 2.2 8 5.1"/><path d="m5.1 8-2.9-.8"/><path d="M14 4.1 12 6"/><path d="m6 12-1.9 2"/></svg>;
}
