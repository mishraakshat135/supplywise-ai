// One small service per backend module. Pages call these; they never use fetch directly.
import { request, post, put, patch } from "./apiClient.js";

export const dashboardService = {
  summary: () => request("/api/dashboard/summary"),
};

export const inventoryService = {
  list: async () => (await request("/api/inventory?limit=500")).items,
  create: (body) => post("/api/inventory", body),
  update: (id, body) => put(`/api/inventory/${id}`, body),
  remove: (id) => request(`/api/inventory/${id}`, { method: "DELETE" }),
};

export const supplierService = {
  list: () => request("/api/suppliers"),
};

export const forecastService = {
  predict: (productId, horizonDays) =>
    post("/api/forecasts/predict", { product_id: productId, horizon_days: horizonDays }),
  latest: (productId) => request(`/api/forecasts/${productId}`),
};

export const procurementService = {
  list: async () => (await request("/api/procurement/recommendations?limit=200")).items,
  generate: (body = {}) => post("/api/procurement/recommendations", body),
  approve: (id) => post(`/api/procurement/recommendations/${id}/approve`, {}),
  reject: (id) => post(`/api/procurement/recommendations/${id}/reject`, {}),
  flag: (id) => post(`/api/procurement/recommendations/${id}/flag`, {}),
};

export const purchaseOrderService = {
  list: async () => (await request("/api/purchase-orders?limit=500")).items,
  get: (id) => request(`/api/purchase-orders/${id}`),
  updateStatus: (id, status) => patch(`/api/purchase-orders/${id}/status`, { status }),
};

export const assistantService = {
  ask: (question) => post("/api/assistant/chat", { question }),
  documents: () => request("/api/documents"),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/documents/upload", { method: "POST", body: form });
  },
  removeDocument: (id) => request(`/api/documents/${id}`, { method: "DELETE" }),
};
