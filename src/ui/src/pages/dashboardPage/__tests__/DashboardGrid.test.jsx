import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// Mock ChartCard to expose title, Download and Open buttons and render children
jest.mock(
  "#components/ChartCard",
  () =>
    ({ title, isDownloading, onDownload, onOpen, widthPercent, children }) => (
      <div>
        <div data-testid="title">{title}</div>
        <button onClick={onDownload}>Download</button>
        <button onClick={onOpen}>Open</button>
        <div data-testid="children">{children}</div>
      </div>
    ),
);

import DashboardGrid from "../DashboardGrid";

const mainCharts = [
  { key: "a", title: "A Chart", chartKey: "aKey" },
  { key: "b", title: "B Chart", chartKey: "bKey" },
];

const rowCharts = [
  { key: "r1", title: "R1", chartKey: "rarefactionCurve", widthPercent: 48 },
];

test("renders main and row charts and wires handlers", () => {
  const handleDownload = jest.fn();
  const handleNavigate = jest.fn();
  const renderDashboardChart = (key) => (
    <div data-testid={`chart-${key}`}>{key}</div>
  );
  const dispatch = jest.fn();
  const selectedAttributeTaxonsetLocal = { attribute: "all", taxonset: "all" };

  render(
    <DashboardGrid
      mainCharts={mainCharts}
      rowCharts={rowCharts}
      renderDashboardChart={renderDashboardChart}
      handleDownload={handleDownload}
      handleNavigate={handleNavigate}
      downloadLoading={{}}
      rarefactionCurveBlob={null}
      clusterSizeDistributionBlob={null}
      selectedAttributeTaxonsetLocal={selectedAttributeTaxonsetLocal}
      dispatch={dispatch}
    />,
  );

  // main titles
  expect(screen.getByText("A Chart")).toBeInTheDocument();
  expect(screen.getByText("B Chart")).toBeInTheDocument();

  // row chart title
  expect(screen.getByText("R1")).toBeInTheDocument();

  // children rendered (multiple cards)
  expect(screen.getAllByTestId("children").length).toBeGreaterThan(0);

  // click download triggers passed download handler via ChartCard
  fireEvent.click(screen.getAllByText("Download")[0]);
  expect(handleDownload).toHaveBeenCalled();

  // click open triggers navigation handler via ChartCard
  fireEvent.click(screen.getAllByText("Open")[0]);
  expect(handleNavigate).toHaveBeenCalled();
});
