import ChartPageShell from "../../components/ChartPageShell";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import React from "react";
import useColumnDescriptionsSets from "#hooks/useColumnDescriptionsSets.js";

const ClusterSummaryPage = ({
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  const { clusterSummary: clusterColumns } = useColumnDescriptionsSets();

  return (
    <ChartPageShell
      title="Cluster Summary"
      chartKey="clusterSummary"
      searchParamKey="CS_code"
      columnDescriptions={clusterColumns}
      initialAttribute={propAttribute}
      initialTaxonset={propTaxonset}
      setSelectedAttributeTaxonsetProp={propSetSelectedAttributeTaxonset}
      renderChart={({ attribute, effectiveColumnDescriptions }) => (
        <ClusterSummary
          attribute={attribute}
          clusterSummaryColumnDescriptions={effectiveColumnDescriptions}
        />
      )}
    />
  );
};

export default ClusterSummaryPage;
