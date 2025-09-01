import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import ClusterSizeDistribution from "../../components/Charts/ClusterSizeDistribution/ClusterSizeDistribution";
import React from "react";
import { handleDownload } from "../../utils/downloadHandlers";
import styles from "./ClusterSizeDistribution.module.scss";

const ClusterSizeDistributionPage = ({ selectedAttributeTaxonset }) => {
  const dispatch = useDispatch();
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading
  );
  const clusterSizeDistributionBlob = useSelector(
    (state) => state?.analysis?.plot?.data?.clusterSizeDistribution
  );

  const handleClose = () => {
    window.history.back();
  };

  return (
    <AppLayout>
      <div className={styles.pageHeader}>
        <AttributeSelector />
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
                selectedAttributeTaxonset,
                clusterSizeDistributionBlob,
              })
            }
            onClose={handleClose}
          >
            <ClusterSizeDistribution />
          </ChartCard>
        </div>
      </div>
    </AppLayout>
  );
};

export default ClusterSizeDistributionPage;
