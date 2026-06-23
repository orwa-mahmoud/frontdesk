import { describe, expect, it } from "vitest";

import { isActivelyProcessing } from "./processing";

describe("isActivelyProcessing", () => {
  const recent = new Date(Date.now() - 1000).toISOString();
  const old = new Date(Date.now() - 20 * 60 * 1000).toISOString(); // 20 min ago, past the 15 min window

  it("is true for a recently-touched in-flight doc", () => {
    expect(isActivelyProcessing({ status: "ingesting", updated_at: recent })).toBe(true);
    expect(isActivelyProcessing({ status: "uploaded", updated_at: recent })).toBe(true);
  });

  it("is false for a stale in-flight doc so polling stops", () => {
    expect(isActivelyProcessing({ status: "ingesting", updated_at: old })).toBe(false);
  });

  it("is false for finished docs regardless of recency", () => {
    expect(isActivelyProcessing({ status: "ready", updated_at: recent })).toBe(false);
    expect(isActivelyProcessing({ status: "failed", updated_at: recent })).toBe(false);
  });
});
