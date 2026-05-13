"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi, campaignApi } from "@/lib/api";
import { Mail, Users, MousePointerClick, TrendingUp } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function DashboardPage() {
  const { data: campaigns } = useQuery({
    queryKey: ["campaigns"],
    queryFn: campaignApi.list,
  });

  const sent    = campaigns?.filter((c) => c.status === "sent").length ?? 0;
  const sending = campaigns?.filter((c) => c.status === "sending").length ?? 0;
  const totalOpens  = campaigns?.reduce((s, c) => s + (c.openCount ?? 0), 0) ?? 0;
  const totalClicks = campaigns?.reduce((s, c) => s + (c.clickCount ?? 0), 0) ?? 0;

  const chartData = campaigns
    ?.filter((c) => c.status === "sent")
    .slice(-6)
    .map((c) => ({
      name: c.name.slice(0, 12),
      opens:  c.openCount  ?? 0,
      clicks: c.clickCount ?? 0,
    })) ?? [];

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={<Mail size={20} />}             label="Campaigns Sent"  value={sent}        />
        <StatCard icon={<TrendingUp size={20} />}       label="In Progress"     value={sending}     color="yellow" />
        <StatCard icon={<Users size={20} />}            label="Total Opens"     value={totalOpens}  color="green" />
        <StatCard icon={<MousePointerClick size={20} />} label="Total Clicks"  value={totalClicks} color="purple" />
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-sm font-medium text-gray-500 mb-4">Recent Campaign Performance</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData}>
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="opens"  fill="#6366f1" radius={[4, 4, 0, 0]} />
              <Bar dataKey="clicks" fill="#a5b4fc" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400 text-sm text-center py-12">No campaign data yet</p>
        )}
      </div>
    </div>
  );
}

function StatCard({
  icon, label, value, color = "indigo",
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color?: "indigo" | "yellow" | "green" | "purple";
}) {
  const colors = {
    indigo: "bg-indigo-50 text-indigo-600",
    yellow: "bg-yellow-50 text-yellow-600",
    green:  "bg-green-50 text-green-600",
    purple: "bg-purple-50 text-purple-600",
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className={`inline-flex p-2 rounded-lg ${colors[color]} mb-3`}>{icon}</div>
      <p className="text-2xl font-semibold text-gray-900">{value.toLocaleString()}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  );
}
