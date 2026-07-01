/**
 * Extracts a human-readable error message from an Axios/HTTP error.
 *
 * FastAPI returns domain errors as `{ detail: string }` (already localized per the
 * request's Accept-Language). We surface that specific message so the user learns
 * *why* an action failed — never a generic "something went wrong" that hides state.
 * Falls back to `fallback` when no usable detail is present.
 */
export function apiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim().length > 0) return detail;
  return fallback;
}
