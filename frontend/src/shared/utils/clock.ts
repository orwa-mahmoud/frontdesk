/**
 * Monotonic clock helper.
 *
 * Wraps `performance.now()` in a plain module function so callers (e.g. timing
 * an async event handler) don't trip the `react-hooks/purity` lint rule, which
 * flags the `performance.now` builtin inside component/hook scopes. Centralizing
 * it here also makes elapsed-time measurement easy to mock in tests.
 *
 * @returns a high-resolution timestamp in milliseconds.
 */
export function monotonicNow(): number {
  return performance.now();
}

/** Milliseconds elapsed since the given {@link monotonicNow} timestamp. */
export function elapsedMsSince(start: number): number {
  return Math.round(monotonicNow() - start);
}
