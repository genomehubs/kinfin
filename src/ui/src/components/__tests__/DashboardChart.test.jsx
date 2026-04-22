import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// Mock ChartCard used by DashboardChart to keep test focused
jest.mock(
  "#components/ChartCard",
  () =>
    ({ title, isDownloading, onDownload, onOpen, widthPercent, children }) => {
      return (
        <div>
          <div data-testid="title">{title}</div>
          <button onClick={onDownload}>Download</button>
          <button onClick={onOpen}>Open</button>
          <div data-testid="children">{children}</div>
        </div>
      );
    },
);

import DashboardChart from "#components/DashboardChart";

test("renders chart and wires download/open handlers", () => {
  const onDownload = jest.fn();
  const onOpen = jest.fn();

  render(
    <DashboardChart
      chartKey="test"
      title="My Chart"
      isDownloading={false}
      onOpen={onOpen}
      onDownload={onDownload}
      renderChart={() => <div>CHART</div>}
    />,
  );

  expect(screen.getByTestId("title")).toHaveTextContent("My Chart");
  expect(screen.getByTestId("children")).toHaveTextContent("CHART");

  fireEvent.click(screen.getByText("Download"));
  expect(onDownload).toHaveBeenCalled();

  fireEvent.click(screen.getByText("Open"));
  expect(onOpen).toHaveBeenCalled();
});
