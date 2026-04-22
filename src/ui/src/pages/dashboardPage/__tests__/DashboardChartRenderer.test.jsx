import React from "react";
import { render, screen } from "@testing-library/react";

jest.mock("#components/Charts/AttributeSummary", () => (props) => (
  <div data-testid="AttributeSummary">attr:{props.attribute}</div>
));
jest.mock("#components/Charts/ClusterSummary", () => (props) => (
  <div data-testid="ClusterSummary">clusterSummary:{props.attribute}</div>
));
jest.mock("#components/Charts/ClusterMetrics", () => (props) => (
  <div data-testid="ClusterMetrics">metrics:{props.attribute}</div>
));
jest.mock("#components/Charts/RarefactionCurve", () => (props) => (
  <div data-testid="RarefactionCurve">rarefaction:{props.attribute}</div>
));
jest.mock("#components/Charts/ClusterSizeDistribution", () => (props) => (
  <div data-testid="ClusterSizeDistribution">csd:{props.attribute}</div>
));

import DashboardChartRenderer from "../DashboardChartRenderer";

const baseProps = {
  selectedAttributeTaxonsetLocal: { attribute: "all", taxonset: "all" },
  attributeSummary: [],
  clusterSummary: [],
  clusterMetrics: [],
  clusterSizeDistributionBlob: null,
};

test("renders AttributeSummary for attributeSummary key", () => {
  render(<DashboardChartRenderer chartKey="attributeSummary" {...baseProps} />);
  expect(screen.getByTestId("AttributeSummary")).toHaveTextContent("attr:all");
});

test("renders ClusterSummary for clusterSummary key", () => {
  render(<DashboardChartRenderer chartKey="clusterSummary" {...baseProps} />);
  expect(screen.getByTestId("ClusterSummary")).toHaveTextContent(
    "clusterSummary:all",
  );
});

test("renders ClusterMetrics for clusterMetrics key", () => {
  render(<DashboardChartRenderer chartKey="clusterMetrics" {...baseProps} />);
  expect(screen.getByTestId("ClusterMetrics")).toHaveTextContent("metrics:all");
});

test("renders RarefactionCurve for rarefactionCurve key", () => {
  render(<DashboardChartRenderer chartKey="rarefactionCurve" {...baseProps} />);
  expect(screen.getByTestId("RarefactionCurve")).toHaveTextContent(
    "rarefaction:all",
  );
});

test("renders ClusterSizeDistribution for clusterSizeDistribution key", () => {
  render(
    <DashboardChartRenderer
      chartKey="clusterSizeDistribution"
      {...baseProps}
    />,
  );
  expect(screen.getByTestId("ClusterSizeDistribution")).toHaveTextContent(
    "csd:all",
  );
});
