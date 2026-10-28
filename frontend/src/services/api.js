const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`);
  } catch {
    throw new Error("Cannot reach the API. Start the FastAPI backend and try again.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `The API request failed (${response.status}).`);
  }
  return response.json();
}

export function getProducts({ q = "", category = "" } = {}) {
  const params = new URLSearchParams({ limit: "100" });
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  return request(`/api/products?${params}`);
}

export function getProduct(productId) {
  return request(`/api/products/${encodeURIComponent(productId)}`);
}

export function getProductRecommendations(productId) {
  return request(
    `/api/recommendations/product/${encodeURIComponent(productId)}?limit=6`,
  );
}

export function getUserRecommendations(userId, maxPrice) {
  const params = new URLSearchParams({ limit: "6", max_price: String(maxPrice) });
  return request(
    `/api/recommendations/user/${encodeURIComponent(userId)}?${params}`,
  );
}

export function getHealth() {
  return request("/api/health");
}
