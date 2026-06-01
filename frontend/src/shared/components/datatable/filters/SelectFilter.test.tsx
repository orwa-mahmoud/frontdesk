import { fireEvent, render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { describe, expect, it, vi } from "vitest";

import { SelectFilter } from "./SelectFilter";
import type { TableSource } from "../hooks/TableSource";
import type { ExtraFilters } from "../types";

function makeSource(extra: ExtraFilters): TableSource<unknown> & { setExtra: ReturnType<typeof vi.fn> } {
  return {
    rows: [],
    total: 0,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    search: "",
    setSearch: vi.fn(),
    sort: null,
    setSort: vi.fn(),
    extra,
    setExtra: vi.fn(),
    clearExtra: vi.fn(),
    page: 1,
    setPage: vi.fn(),
    pageSize: 20,
    setPageSize: vi.fn(),
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    isFetchingNextPage: false,
    mode: "frontend",
  } as unknown as TableSource<unknown> & { setExtra: ReturnType<typeof vi.fn> };
}

function renderFilter(source: TableSource<unknown>) {
  return render(
    <MantineProvider>
      <SelectFilter
        source={source}
        filterKey="status"
        label="Status"
        data={[
          { value: "ready", label: "Ready" },
          { value: "failed", label: "Failed" },
        ]}
      />
    </MantineProvider>,
  );
}

describe("SelectFilter", () => {
  it("shows the current string value", () => {
    renderFilter(makeSource({ status: "ready" }));
    expect(screen.getByDisplayValue("Ready")).toBeInTheDocument();
  });

  it("coerces non-string extra values without crashing", () => {
    // A numeric extra value should not crash; it is stringified for the Select.
    expect(() => renderFilter(makeSource({ status: 42 as unknown as string }))).not.toThrow();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("clears the filter to undefined via the clear button", () => {
    const source = makeSource({ status: "ready" });
    const { container } = renderFilter(source);
    // Mantine renders a CloseButton when clearable + a value is set.
    const clearBtn = container.querySelector("button");
    expect(clearBtn).not.toBeNull();
    fireEvent.click(clearBtn!);
    expect(source.setExtra).toHaveBeenCalledWith("status", undefined);
  });
});
