import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// Mocks for hooks used inside useDashboardData
const mockUsePlot = jest.fn();
const mockUseSessionPolling = jest.fn();
const mockUseColumnDescriptions = jest.fn();
const mockUseColumnDescriptionsSets = jest.fn();

jest.mock("#hooks/usePlot", () => (args, opts) => mockUsePlot(args, opts));
jest.mock("#hooks/useSessionPolling", () => (id) => mockUseSessionPolling(id));
jest.mock(
  "#hooks/useColumnDescriptions",
  () => () => mockUseColumnDescriptions(),
);
jest.mock(
  "#hooks/useColumnDescriptionsSets",
  () => () => mockUseColumnDescriptionsSets(),
);

// Mock react-router useParams
jest.mock("react-router-dom", () => ({
  useParams: () => ({ sessionId: "s1" }),
  useSearchParams: () => [new URLSearchParams()],
}));

// Mock react-redux hooks
const mockDispatch = jest.fn();
let mockState = {};
jest.mock("react-redux", () => ({
  useDispatch: () => mockDispatch,
  useSelector: (fn) => fn(mockState),
}));

import useDashboardData from "../useDashboardData";

function TestComp() {
  const data = useDashboardData();
  return (
    <div>
      <div data-testid="rare-data">{String(data.rarefactionCurve.data)}</div>
      <div data-testid="csd-data">
        {String(data.clusterSizeDistribution.data)}
      </div>
      <div data-testid="is-plots-loading">{String(data.isPlotsLoading)}</div>
      <div data-testid="is-session-active">{String(data.isSessionActive)}</div>
      <div data-testid="ready-for-analysis">
        {String(data.readyForAnalysis)}
      </div>
    </div>
  );
}

describe("useDashboardData", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // default mock state
    mockState = {
      config: {
        data: {
          s1: { status: "active", config: { foo: "bar" } },
        },
        uiState: {
          selectedAttributeTaxonset: { attribute: "all", taxonset: "all" },
          downloadLoading: {},
        },
      },
    };

    mockUseColumnDescriptions.mockReturnValue({ data: [] });
    mockUseColumnDescriptionsSets.mockReturnValue({
      attributeSummary: [],
      clusterSummary: [],
      clusterMetrics: [],
    });

    mockUseSessionPolling.mockReturnValue({
      sessionMeta: { data: { status: "completed", isComplete: true } },
      sessionLoading: false,
      isLoadingSession: false,
      error: null,
    });

    mockUsePlot.mockImplementation((args) => {
      if (args.plotType === "rarefaction-curve") {
        return { data: "blob1", isLoading: false, error: null };
      }
      if (args.plotType === "cluster-size-distribution") {
        return { data: "blob2", isLoading: false, error: null };
      }
      return { data: null, isLoading: false, error: null };
    });
  });

  test("normalizes blobs and computes flags", async () => {
    render(<TestComp />);

    await waitFor(() => {
      expect(screen.getByTestId("rare-data").textContent).toBe("blob1");
      expect(screen.getByTestId("csd-data").textContent).toBe("blob2");
      expect(screen.getByTestId("is-plots-loading").textContent).toBe("false");
      expect(screen.getByTestId("is-session-active").textContent).toBe("true");
      expect(screen.getByTestId("ready-for-analysis").textContent).toBe("true");
    });
  });

  test("reflects plots loading state", async () => {
    mockUsePlot.mockImplementation((args) => {
      if (args.plotType === "rarefaction-curve") {
        return { data: null, isLoading: true, error: null };
      }
      if (args.plotType === "cluster-size-distribution") {
        return { data: null, isLoading: false, error: null };
      }
      return { data: null, isLoading: false, error: null };
    });

    render(<TestComp />);

    await waitFor(() => {
      expect(screen.getByTestId("is-plots-loading").textContent).toBe("true");
      expect(screen.getByTestId("rare-data").textContent).toBe("null");
    });
  });
});
