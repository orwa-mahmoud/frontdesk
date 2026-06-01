import { describe, expect, it, vi } from "vitest";

import { elapsedMsSince, monotonicNow } from "./clock";

describe("clock", () => {
  it("monotonicNow returns a number", () => {
    expect(typeof monotonicNow()).toBe("number");
  });

  it("elapsedMsSince rounds the delta from a start timestamp", () => {
    const spy = vi.spyOn(performance, "now");
    spy.mockReturnValueOnce(1000).mockReturnValueOnce(1250.4);
    const start = monotonicNow(); // 1000
    expect(elapsedMsSince(start)).toBe(250); // round(1250.4 - 1000)
    spy.mockRestore();
  });
});
