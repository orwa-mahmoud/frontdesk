import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MantineProvider } from "@mantine/core";

vi.mock("../../auth/useAuth", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "owner@acme.com",
      full_name: "Acme Owner",
      is_active: true,
      tenant: { id: "t1", slug: "acme", name: "Acme Corp", role: "owner" },
    },
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

import { ProtectedShell } from "./AppShell";

function wrap(ui: React.ReactNode) {
  return (
    <MantineProvider>
      <MemoryRouter>{ui}</MemoryRouter>
    </MantineProvider>
  );
}

describe("ProtectedShell", () => {
  it("renders the brand name", () => {
    render(wrap(<ProtectedShell><div>Page</div></ProtectedShell>));
    expect(screen.getByText("frontdesk")).toBeInTheDocument();
  });

  it("renders all nav links", () => {
    render(wrap(<ProtectedShell><div>Page</div></ProtectedShell>));
    expect(screen.getByText("Inbox")).toBeInTheDocument();
    expect(screen.getByText("Chat (test)")).toBeInTheDocument();
    expect(screen.getByText("Conversations")).toBeInTheDocument();
    expect(screen.getByText("Documents")).toBeInTheDocument();
    expect(screen.getByText("Usage & cost")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("renders user display name", () => {
    render(wrap(<ProtectedShell><div>Page</div></ProtectedShell>));
    expect(screen.getByText("Acme Owner")).toBeInTheDocument();
  });

  it("renders tenant name", () => {
    render(wrap(<ProtectedShell><div>Page</div></ProtectedShell>));
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
  });

  it("renders tenant slug in sidebar", () => {
    render(wrap(<ProtectedShell><div>Page</div></ProtectedShell>));
    expect(screen.getByText("acme")).toBeInTheDocument();
  });

  it("renders sign out button", () => {
    render(wrap(<ProtectedShell><div>Page</div></ProtectedShell>));
    expect(screen.getByLabelText("Sign out")).toBeInTheDocument();
  });

  it("renders children in main area", () => {
    render(wrap(<ProtectedShell><div>My Page Content</div></ProtectedShell>));
    expect(screen.getByText("My Page Content")).toBeInTheDocument();
  });

  it("renders avatar with first letter of name", () => {
    render(wrap(<ProtectedShell><div>Page</div></ProtectedShell>));
    expect(screen.getByText("A")).toBeInTheDocument();
  });
});
