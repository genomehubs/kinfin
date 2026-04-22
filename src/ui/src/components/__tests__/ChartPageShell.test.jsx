import React from "react";
import { render, screen } from "@testing-library/react";

// Mock layout, attribute selector, base page and custom dialog used by ChartPageShell
jest.mock("../AppLayout", () => ({ children }) => (
  <div data-testid="layout">{children}</div>
));

jest.mock(
  "../AttributeSelector",
  () =>
    ({ attribute, taxonset, setSelectedAttributeTaxonset }) => (
      <div data-testid="attr-selector">
        {attribute}:{taxonset}
      </div>
    ),
);

jest.mock(
  "../BaseChartPage",
  () =>
    ({
      title,
      isDownloading,
      onDownload,
      onCustomise,
      onClose,
      customiseProps,
      children,
    }) => (
      <div>
        <div data-testid="base-title">{title}</div>
        <div data-testid="base-children">{children}</div>
      </div>
    ),
);

jest.mock("../CustomisationDialog", () => (props) => (
  <div data-testid="custom-dialog">{props.title}</div>
));

// Mock hooks used inside ChartPageShell
jest.mock("#hooks/useColumnDescriptions.js", () => () => ({ data: ["colA"] }));
jest.mock("#hooks/usePageCustomisation", () => () => ({
  selectedCodes: ["c1"],
  customiseOpen: true,
  openCustomise: () => {},
  handleApply: () => {},
  handleCancel: () => {},
}));
jest.mock("#hooks/useNavigateBack", () => () => jest.fn());

// Mock react-redux hooks so tests don't need a Provider
jest.mock("react-redux", () => ({
  useDispatch: () => jest.fn(),
  useSelector: (selector) =>
    selector({
      config: {
        uiState: {
          selectedAttributeTaxonset: { attribute: "attr", taxonset: "tax" },
        },
      },
    }),
}));

import ChartPageShell from "../ChartPageShell";

test("renders shell, attribute selector and chart content", () => {
  render(
    <ChartPageShell
      title="My Chart"
      chartKey="mychart"
      searchParamKey="X"
      columnDescriptions={["colA"]}
      initialAttribute={"attr"}
      initialTaxonset={"tax"}
      setSelectedAttributeTaxonsetProp={() => {}}
      renderChart={({ attribute }) => (
        <div data-testid="inner">{attribute}</div>
      )}
    />,
  );

  expect(screen.getByTestId("layout")).toBeInTheDocument();
  expect(screen.getByTestId("attr-selector")).toHaveTextContent("attr:tax");
  expect(screen.getByTestId("base-title")).toHaveTextContent("My Chart");
  expect(screen.getByTestId("inner")).toHaveTextContent("attr");
  expect(screen.getByTestId("custom-dialog")).toHaveTextContent(
    "Customise My Chart",
  );
});
