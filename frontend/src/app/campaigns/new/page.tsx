"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { campaignApi, type GenerateRequest } from "@/lib/api";
import { Sparkles, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

export default function NewCampaignPage() {
  const router = useRouter();
  const qc     = useQueryClient();

  const [form, setForm] = useState({
    name:        "",
    subject:     "",
    fromAddress: "",
    listId:      "",
    htmlContent: "",
  });

  const [aiPrompt, setAiPrompt] = useState("");
  const [aiTone, setAiTone] = useState<GenerateRequest["tone"]>("professional");

  const generateMutation = useMutation({
    mutationFn: campaignApi.generate,
    onSuccess: (data) => {
      setForm((f) => ({
        ...f,
        subject:     data.subject,
        htmlContent: data.htmlContent,
      }));
    },
  });

  const createMutation = useMutation({
    mutationFn: () => campaignApi.create({ ...form, status: "draft" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      router.push("/campaigns");
    },
  });

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">New Campaign</h1>

      <div className="space-y-6">
        {/* AI Generation */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={16} className="text-indigo-600" />
            <span className="text-sm font-medium text-indigo-700">Generate with AI</span>
          </div>
          <textarea
            className="w-full border border-indigo-200 rounded-lg p-3 text-sm bg-white resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400"
            rows={3}
            placeholder="Describe your campaign… e.g. 'Monthly newsletter for a coffee subscription service with a seasonal promotion'"
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
          />
          <div className="flex items-center gap-3 mt-3">
            <select
              className="text-sm border border-indigo-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none"
              value={aiTone}
              onChange={(e) => setAiTone(e.target.value as any)}
            >
              <option value="professional">Professional</option>
              <option value="friendly">Friendly</option>
              <option value="urgent">Urgent</option>
            </select>
            <button
              onClick={() => generateMutation.mutate({ prompt: aiPrompt, tone: aiTone })}
              disabled={!aiPrompt || generateMutation.isPending}
              className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {generateMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              Generate
            </button>
          </div>
        </div>

        {/* Form */}
        <Field label="Campaign Name">
          <input className={input} value={form.name} onChange={set("name")} placeholder="Q3 Newsletter" />
        </Field>
        <Field label="Subject Line">
          <input className={input} value={form.subject} onChange={set("subject")} placeholder="Your subject line" />
        </Field>
        <Field label="From Address">
          <input className={input} value={form.fromAddress} onChange={set("fromAddress")} placeholder="hello@yourdomain.com" type="email" />
        </Field>
        <Field label="Contact List ID">
          <input className={input} value={form.listId} onChange={set("listId")} placeholder="list-abc123" />
        </Field>
        <Field label="HTML Content">
          <textarea
            className={`${input} font-mono text-xs`}
            rows={10}
            value={form.htmlContent}
            onChange={set("htmlContent")}
            placeholder="<p>Your email HTML here…</p>"
          />
        </Field>

        <div className="flex gap-3 pt-2">
          <button
            onClick={() => createMutation.mutate()}
            disabled={!form.name || !form.subject || createMutation.isPending}
            className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {createMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
            Save as Draft
          </button>
          <button
            onClick={() => router.back()}
            className="px-5 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

const input = "w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      {children}
    </div>
  );
}
