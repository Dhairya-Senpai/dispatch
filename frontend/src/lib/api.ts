import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    "Content-Type": "application/json",
    "x-api-key": process.env.NEXT_PUBLIC_API_KEY ?? "",
  },
});

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Campaign {
  campaignId: string;
  name: string;
  subject: string;
  status: "draft" | "sending" | "sent" | "scheduled";
  fromAddress: string;
  listId: string;
  htmlContent: string;
  createdAt: string;
  sentAt?: string;
  openCount?: number;
  clickCount?: number;
  bounceCount?: number;
  queuedCount?: number;
}

export interface Contact {
  contactId: string;
  email: string;
  firstName?: string;
  lastName?: string;
  listId: string;
  createdAt: string;
  status: "subscribed" | "unsubscribed" | "bounced";
}

export interface GenerateRequest {
  prompt: string;
  brandName?: string;
  tone?: "professional" | "friendly" | "urgent";
  campaignType?: "newsletter" | "promotional" | "transactional";
}

export interface GenerateResponse {
  subject: string;
  previewText: string;
  htmlContent: string;
  plainText: string;
}

// ── Campaign endpoints ────────────────────────────────────────────────────────

export const campaignApi = {
  list: () =>
    api.get<Campaign[]>("/campaigns").then((r) => r.data),

  get: (id: string) =>
    api.get<Campaign>(`/campaigns/${id}`).then((r) => r.data),

  create: (data: Partial<Campaign>) =>
    api.post<Campaign>("/campaigns", data).then((r) => r.data),

  update: (id: string, data: Partial<Campaign>) =>
    api.put<Campaign>(`/campaigns/${id}`, data).then((r) => r.data),

  send: (id: string) =>
    api.post<{ queued: number; failed: number }>(`/campaigns/${id}/send`).then((r) => r.data),

  generate: (data: GenerateRequest) =>
    api.post<GenerateResponse>("/campaigns/generate", data).then((r) => r.data),
};

// ── Contact endpoints ─────────────────────────────────────────────────────────

export const contactApi = {
  list: (listId?: string) =>
    api.get<Contact[]>("/contacts", { params: { listId } }).then((r) => r.data),

  create: (data: Partial<Contact>) =>
    api.post<Contact>("/contacts", data).then((r) => r.data),

  delete: (id: string) =>
    api.delete(`/contacts/${id}`).then((r) => r.data),

  import: (listId: string, emails: string[]) =>
    api.post("/contacts/import", { listId, emails }).then((r) => r.data),
};

// ── Analytics endpoints ───────────────────────────────────────────────────────

export const analyticsApi = {
  getCampaignStats: (campaignId: string) =>
    api.get(`/analytics/campaigns/${campaignId}`).then((r) => r.data),

  getOverview: () =>
    api.get("/analytics/overview").then((r) => r.data),
};

export default api;
