import React from "react";
import { useSelector } from "react-redux";
import ChartPageShell from "../../components/ChartPageShell";
import ClusterSizeDistribution from "../../components/Charts/ClusterSizeDistribution";

const ClusterSizeDistributionPage = ({
  clusterSizeDistributionBlob,
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading,
  );

  const isDownloading =
    downloadLoading?.downloadLoading?.ClusterSizeDistribution;

  return (
    <ChartPageShell
      title="Cluster Size Distribution"
      chartKey="clusterSizeDistribution"
      searchParamKey={null}
      isDownloading={isDownloading}
      initialAttribute={propAttribute}
      initialTaxonset={propTaxonset}
      setSelectedAttributeTaxonsetProp={propSetSelectedAttributeTaxonset}
      blob={clusterSizeDistributionBlob}
      renderChart={({ attribute }) => (
        <ClusterSizeDistribution
          attribute={attribute}
          clusterSizeDistributionBlob={clusterSizeDistributionBlob}
        />
      )}
    />
  );
};

export default ClusterSizeDistributionPage;
