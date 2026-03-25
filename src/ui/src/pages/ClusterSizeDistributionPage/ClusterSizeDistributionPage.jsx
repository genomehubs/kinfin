import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import ClusterSizeDistribution from "../../components/Charts/ClusterSizeDistribution";
import React from "react";
import { handleDownload } from "../../utils/downloadHandlers";
import styles from "./ClusterSizeDistribution.module.scss";

const ClusterSizeDistributionPage = ({
  selectedAttributeTaxonset: _selectedAttributeTaxonset,
  clusterSizeDistributionBlob,
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  const dispatch = useDispatch();
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading,
  );

  const handleClose = () => {
    window.history.back();
  };

  const selectedFromStore = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset,
  );

  const attribute = propAttribute ?? selectedFromStore?.attribute ?? "all";
  const taxonset = propTaxonset ?? selectedFromStore?.taxonset ?? "all";

  const setSelectedAttributeTaxonset =
    propSetSelectedAttributeTaxonset ??
    ((payload) =>
      dispatch({ type: "uiState/setSelectedAttributeTaxonset", payload }));

  const effectiveSelected = { attribute, taxonset };

  return (
    <AppLayout>
      <div className={styles.pageHeader}>
        <AttributeSelector
          attribute={attribute}
          taxonset={taxonset}
          setSelectedAttributeTaxonset={setSelectedAttributeTaxonset}
        />
      </div>
      <div className={styles.page}>
        <div className={styles.chartsContainer}>
          <ChartCard
            title="Cluster Size Distribution"
            isDownloading={
              downloadLoading?.downloadLoading?.ClusterSizeDistribution
            }
            onDownload={() =>
              handleDownload({
                chartKey: "clusterSizeDistribution",
                dispatch,
                selectedAttributeTaxonset: effectiveSelected,
                clusterSizeDistributionBlob,
              })
            }
            onClose={handleClose}
          >
            <ClusterSizeDistribution
              attribute={attribute}
              clusterSizeDistributionBlob={clusterSizeDistributionBlob}
            />
          </ChartCard>
        </div>
      </div>
    </AppLayout>
  );
};

export default ClusterSizeDistributionPage;
