import { act, fireEvent, render } from "@testing-library/react";

import ClusterSummary from "#components/Charts/ClusterSummary/ClusterSummary";
import { MemoryRouter } from "react-router-dom";
import React from "react";

// Mock MUI DataGrid to avoid TextEncoder/environment issues in Jest
jest.mock("@mui/x-data-grid", () => ({
  DataGrid: (props) => {
    const React = require("react");
    return React.createElement("div", { "data-testid": "datagrid" }, null);
  },
}));

// Mock hooks and API used inside ClusterSummary
jest.mock("#store/api", () => ({
  useGetClusterSummaryQuery: jest.fn(() => ({ data: null })),
}));

jest.mock(
  "#hooks/usePageCustomisation",
  () =>
    jest.fn(() => ({
      selectedCodes: [],
      setSelectedCodes: jest.fn(),
    })),
  { virtual: true },
);

jest.mock("#hooks/useIsCurrentPage", () => jest.fn(() => true));
jest.mock("#hooks/useFullscreen", () =>
  jest.fn(() => ({ isFullScreen: false })),
);


describe("ClusterSummary column duplication repro", () => {
  const sampleColumnDescriptions = [
    {
      code: "C1",
      name: "pfam_X_count",
      alias: "Pfam X Count",
      isDefault: true,
    },
    { code: "C2", name: "gene_count", alias: "Gene Count", isDefault: true },
  ];

  const sampleData = {
    1: { id: "r1", pfam_A_count: 1, pfam_B_count: 2, gene_count: 3 },
  };

  beforeEach(() => {
    jest.resetModules();
  });

  test("no duplicate column headers after scroll/mouseout", async () => {
    const api = require("#store/api");
    api.useGetClusterSummaryQuery.mockReturnValue({
      data: { data: sampleData, total_entries: 1 },
    });

    const usePageCustomisation = require("#hooks/usePageCustomisation");
    usePageCustomisation.mockReturnValue({
      selectedCodes: ["C1", "C2"],
      setSelectedCodes: jest.fn(),
    });

    const { container } = render(
      <MemoryRouter>
        <ClusterSummary
          attribute={"attr1"}
          clusterSummaryColumnDescriptions={sampleColumnDescriptions}
        />
      </MemoryRouter>,
    );

    // Wait for initial render
    await act(async () => {});

    const headerNodes = container.querySelectorAll(
      ".MuiDataGrid-columnHeaderTitle",
    );
    const headerTexts = Array.from(headerNodes).map(
      (n) => n.textContent?.trim() || "",
    );

    // Ensure headers are unique initially
    const uniqueInitial = new Set(headerTexts);
    expect(uniqueInitial.size).toBe(headerTexts.length);

    // Simulate user scroll and mouseout which previously triggered duplication
    const gridWrapper =
      container.querySelector(".MuiDataGrid-root") || container.firstChild;
    act(() => {
      fireEvent.scroll(gridWrapper, { target: { scrollLeft: 50 } });
    });

    // Fire a mouseout on header area
    const headerArea = container.querySelector(".MuiDataGrid-columnHeaders");
    if (headerArea) {
      act(() => {
        fireEvent.mouseOut(headerArea);
      });
    }

    // Re-query headers
    const headerNodesAfter = container.querySelectorAll(
      ".MuiDataGrid-columnHeaderTitle",
    );
    const headerTextsAfter = Array.from(headerNodesAfter).map(
      (n) => n.textContent?.trim() || "",
    );

    const uniqueAfter = new Set(headerTextsAfter);
    expect(uniqueAfter.size).toBe(headerTextsAfter.length);
  });
});
