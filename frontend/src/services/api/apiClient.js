// Talks to the FastAPI backend. The base URL comes from frontend/.env (VITE_API_BASE_URL).
const baseUrl = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function request(path, options = {}) {
  const isForm = options.body instanceof FormData;
  // For file uploads the browser must set the multipart Content-Type itself.
  const headers = isForm
    ? { ...options.headers }
    : { "Content-Type": "application/json", ...options.headers };

  let response;
  try {
    response = await fetch(`${baseUrl}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(`Cannot reach the backend at ${baseUrl}. Is it running?`, 0);
  }

  if (response.status === 204) return null;

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    /* empty or non-JSON body */
  }

  if (!response.ok) {
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join("; ")
          : `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return payload;
}

export const post = (path, body) =>
  request(path, { method: "POST", body: JSON.stringify(body ?? {}) });
export const put = (path, body) =>
  request(path, { method: "PUT", body: JSON.stringify(body ?? {}) });
export const patch = (path, body) =>
  request(path, { method: "PATCH", body: JSON.stringify(body ?? {}) });
