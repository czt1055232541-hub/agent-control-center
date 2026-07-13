import type { ComponentStatus } from "../types";

export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string;
  readonly detail: unknown;
  readonly requestId?: string;

  constructor(message: string, options: { status: number; errorCode: string; detail?: unknown; requestId?: string }) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.errorCode = options.errorCode;
    this.detail = options.detail;
    this.requestId = options.requestId;
  }
}

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
    const payload = data && typeof data === "object" ? data as Record<string, unknown> : {};
    const detail = payload.detail;
    const message = typeof payload.message === "string"
      ? payload.message
      : typeof detail === "string"
        ? detail
        : `${response.status} ${response.statusText}`;
    const errorCode = typeof payload.error_code === "string" ? payload.error_code : `HTTP_${response.status}`;
    const requestId = typeof payload.request_id === "string"
      ? payload.request_id
      : response.headers.get("X-Request-ID") ?? undefined;
    throw new ApiError(message, { status: response.status, errorCode, detail, requestId });
  }
  return data as T;
}
