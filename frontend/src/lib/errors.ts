import { ApiError } from "@/lib/api";

export function errorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | null)?.detail;
    if (typeof detail === "string" && detail.length > 0) return detail;
  }
  if (error instanceof Error && error.message.length > 0) return error.message;
  return fallback;
}
