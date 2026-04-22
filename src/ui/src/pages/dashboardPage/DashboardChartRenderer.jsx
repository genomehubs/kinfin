import React from "react";
import AttributeSummary from "#components/Charts/AttributeSummary";
import ClusterSummary from "#components/Charts/ClusterSummary";
import ClusterMetrics from "#components/Charts/ClusterMetrics";
import RarefactionCurve from "#components/Charts/RarefactionCurve";
import ClusterSizeDistribution from "#components/Charts/ClusterSizeDistribution";

const DashboardChartRenderer = ({
  chartKey,
  selectedAttributeTaxonsetLocal,
  attributeSummary,
  clusterSummary,
  clusterMetrics,
  clusterSizeDistributionBlob,
}) => {
  switch (chartKey) {
    case "attributeSummary":
      return (
        <AttributeSummary
          attribute={selectedAttributeTaxonsetLocal.attribute}
          attributeSummaryColumnDescriptions={attributeSummary}
        />
      );
    case "clusterSummary":
      return (
        <ClusterSummary
          attribute={selectedAttributeTaxonsetLocal.attribute}
          clusterSummaryColumnDescriptions={clusterSummary}
        />
      );
    case "clusterMetrics":
      return (
        <ClusterMetrics
          attribute={selectedAttributeTaxonsetLocal.attribute}
          taxonset={selectedAttributeTaxonsetLocal.taxonset}
          clusterMetricsColumnDescriptions={clusterMetrics}
        />
      );
    case "rarefactionCurve":
      return (
        <RarefactionCurve
          attribute={selectedAttributeTaxonsetLocal.attribute}
        />
      );
    case "clusterSizeDistribution":
      return (
        <ClusterSizeDistribution
          attribute={selectedAttributeTaxonsetLocal.attribute}
          clusterSizeDistributionBlob={clusterSizeDistributionBlob}
        />
      );
    default:
      return null;
  }
};

export default DashboardChartRenderer;
