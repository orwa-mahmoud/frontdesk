import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const mockRender = vi.fn();
vi.mock("react-dom/client", () => ({
  createRoot: vi.fn(() => ({ render: mockRender })),
}));

vi.mock("./app/Providers", () => ({
  Providers: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("./app/router", () => ({
  AppRoutes: () => null,
}));

describe("main", () => {
  let rootEl: HTMLDivElement;

  beforeEach(() => {
    rootEl = document.createElement("div");
    rootEl.id = "root";
    document.body.appendChild(rootEl);
  });

  afterEach(() => {
    rootEl.remove();
    vi.resetModules();
  });

  it("creates root and renders the app", async () => {
    const { createRoot } = await import("react-dom/client");
    await import("./main");
    expect(createRoot).toHaveBeenCalledWith(rootEl);
    expect(mockRender).toHaveBeenCalled();
  });
});
