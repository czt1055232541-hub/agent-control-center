import type { ComponentStatus } from "../types";

export function isRunning(component: ComponentStatus): boolean {
  return component.pid_running || component.port_listening;
}

export async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    const body = await response.text().catch(() => "");
    const preview = body.replace(/\s+/g, " ").trim().slice(0, 120);
    throw new Error(preview ? `Expected JSON from ${url}, got ${contentType}: ${preview}` : `Expected JSON from ${url}, got ${contentType || "unknown content type"}`);
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data);
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return data as T;
}
