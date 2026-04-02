import React from "react";
import { render, screen } from "@testing-library/react";

// Mock ChartCard and CustomisationDialog to inspect props
jest.mock(
  "../../components/ChartCard",
  () =>
    ({ title, isDownloading, onDownload, onCustomise, onClose, children }) => (
      <div>
        <div data-testid="chartcard-title">{title}</div>
        <div data-testid="chartcard-children">{children}</div>
      </div>
    ),
);

jest.mock("../../components/CustomisationDialog", () => (props) => (
  <div data-testid="custom-dialog">{props.title}</div>
));

import BaseChartPage from "../../components/BaseChartPage";

test("renders children and passes customiseProps to dialog", () => {
  render(
    <BaseChartPage
      title="T"
      isDownloading={false}
      onDownload={() => {}}
      onCustomise={() => {}}
      onClose={() => {}}
      customiseProps={{
        open: true,
        onClose: () => {},
        onApply: () => {},
        selectedCodes: ["a"],
        columnDescriptions: [],
        title: "Custom Title",
      }}
    >
      <div>INNER</div>
    </BaseChartPage>,
  );

  expect(screen.getByTestId("chartcard-title")).toHaveTextContent("T");
  expect(screen.getByTestId("chartcard-children")).toHaveTextContent("INNER");
  expect(screen.getByTestId("custom-dialog")).toHaveTextContent("Custom Title");
});
