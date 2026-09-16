import { getAuthenticatedUser } from "@/lib/firebase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}, timeoutMs = 30_000): Promise<T> {
  const token = await (await getAuthenticatedUser())?.getIdToken();
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const cancel = () => controller.abort();
  init.signal?.addEventListener("abort", cancel, { once: true });
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers
      }
    });
  } catch {
    if (controller.signal.aborted) throw new ApiError(408, "The request timed out or was cancelled. Please try again.");
    throw new ApiError(0, "Could not reach the secure API. Check your connection and try again.");
  } finally {
    window.clearTimeout(timeout);
    init.signal?.removeEventListener("abort", cancel);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.error?.message ?? body?.detail ?? "Request failed");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
