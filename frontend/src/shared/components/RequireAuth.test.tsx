import { describe, it, expect } from "vitest";

describe("RequireAuth", () => {
  it("module exports RequireAuth function", async () => {
    const mod = await import("./RequireAuth");
    expect(typeof mod.RequireAuth).toBe("function");
  });
});
