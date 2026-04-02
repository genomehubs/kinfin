import ChartPageShell from "../../components/ChartPageShell";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import React from "react";
import useColumnDescriptionsSets from "#hooks/useColumnDescriptionsSets.js";

const ClusterMetricsPage = ({
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  const { clusterMetrics: metricsColumns } = useColumnDescriptionsSets();

  return (
    <ChartPageShell
      title="Cluster Metrics"
      chartKey="clusterMetrics"
      searchParamKey="CM_code"
      columnDescriptions={metricsColumns}
      initialAttribute={propAttribute}
      initialTaxonset={propTaxonset}
      setSelectedAttributeTaxonsetProp={propSetSelectedAttributeTaxonset}
      renderChart={({ attribute, taxonset, effectiveColumnDescriptions }) => (
        <ClusterMetrics
          attribute={attribute}
          taxonset={taxonset}
          clusterMetricsColumnDescriptions={effectiveColumnDescriptions}
        />
      )}
    />
  );
};

export default ClusterMetricsPage;
