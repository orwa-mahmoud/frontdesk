import { describe, expect, it } from "vitest";

import { apiErrorMessage } from "./apiError";

describe("apiErrorMessage", () => {
  it("returns the backend detail string when present", () => {
    const err = { response: { data: { detail: "Changing the model would break search." } } };
    expect(apiErrorMessage(err, "fallback")).toBe("Changing the model would break search.");
  });

  it("falls back when detail is missing", () => {
    expect(apiErrorMessage({ response: { data: {} } }, "fallback")).toBe("fallback");
    expect(apiErrorMessage(new Error("boom"), "fallback")).toBe("fallback");
    expect(apiErrorMessage(undefined, "fallback")).toBe("fallback");
  });

  it("falls back when detail is not a non-empty string", () => {
    expect(apiErrorMessage({ response: { data: { detail: "" } } }, "fallback")).toBe("fallback");
    expect(apiErrorMessage({ response: { data: { detail: "   " } } }, "fallback")).toBe("fallback");
    expect(apiErrorMessage({ response: { data: { detail: 42 } } }, "fallback")).toBe("fallback");
    expect(apiErrorMessage({ response: { data: { detail: ["a", "b"] } } }, "fallback")).toBe("fallback");
  });
});
