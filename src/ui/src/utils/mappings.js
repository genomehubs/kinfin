const chartNameMapping = {
  attributeSummary: "Attribute Summary",
  clusterMetrics: "Cluster Metrics",
  clusterSizeDistribution: "Cluster Size Distribution",
  clusterSummary: "Cluster Summary",
  rarefactionCurve: "Rarefaction Curve",
};

const mapChartName = (chartKey) => chartNameMapping[chartKey] || chartKey || "";

export { chartNameMapping, mapChartName };
