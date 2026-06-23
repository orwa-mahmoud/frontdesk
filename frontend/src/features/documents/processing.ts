const PROCESSING_STATUSES = new Set(["uploaded", "ingesting"]);
// Mirrors the backend INGESTION_STALE_AFTER_SECONDS default (15 min): once a doc has
// sat in-flight this long the reaper owns it, so stop polling for it here too — the
// backend /processing endpoint drops it for the same reason.
const STALE_AFTER_MS = 15 * 60 * 1000;

/** A document still worth polling: in flight (uploaded/ingesting) AND touched
 * recently. A stale in-flight doc is left to the reaper, so the UI stops polling it. */
export function isActivelyProcessing(doc: { status: string; updated_at: string }): boolean {
  return PROCESSING_STATUSES.has(doc.status) && Date.now() - new Date(doc.updated_at).getTime() < STALE_AFTER_MS;
}
