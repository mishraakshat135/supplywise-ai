const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
export async function request(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}
// No API routes are confirmed yet. Feature services intentionally use demo fixtures until contracts are agreed.
