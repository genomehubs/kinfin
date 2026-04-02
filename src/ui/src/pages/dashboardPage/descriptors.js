import { mapChartName } from "../../utils/mappings";

export const mainCharts = [
  {
    key: "attributeSummary",
    title: mapChartName("attributeSummary"),
    chartKey: "attributeSummary",
  },
  {
    key: "clusterSummary",
    title: mapChartName("clusterSummary"),
    chartKey: "clusterSummary",
  },
  {
    key: "clusterMetrics",
    title: mapChartName("clusterMetrics"),
    chartKey: "clusterMetrics",
  },
];

export const rowCharts = [
  {
    key: "rarefactionCurve",
    title: mapChartName("rarefactionCurve"),
    chartKey: "rarefactionCurve",
    widthPercent: 48,
    includesBlob: true,
  },
  {
    key: "clusterSizeDistribution",
    title: mapChartName("clusterSizeDistribution"),
    chartKey: "clusterSizeDistribution",
    widthPercent: 48,
    includesBlob: true,
  },
];

export default { mainCharts, rowCharts };
