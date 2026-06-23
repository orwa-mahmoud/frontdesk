// Display date formatters built on the native Intl API — replaces the dayjs
// dependency. Locale is pinned to en-US so output is byte-identical to the
// previous dayjs formats; switch to the active i18n locale here if/when localized
// dates are wanted.
const dateTimeFmt = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const dateFmt = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

/** "Jan 5, 14:30" — was dayjs(iso).format("MMM D, HH:mm"). */
export function formatDateTime(iso: string): string {
  return dateTimeFmt.format(new Date(iso));
}

/** "Jan 5, 2026" — was dayjs(iso).format("MMM D, YYYY"). */
export function formatDate(iso: string): string {
  return dateFmt.format(new Date(iso));
}
