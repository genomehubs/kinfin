import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import ClusterSizeDistribution from "../../components/Charts/ClusterSizeDistribution";
import React from "react";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { getAttributeSummary } from "../../app/store/analysis/slices/attributeSummarySlice";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import styles from "./ClusterSizeDistribution.module.scss";

const ClusterSizeDistributionPage = () => {
  const dispatch = useDispatch();
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset
  );
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading
  );

  const handleDownload = () => {
    dispatch(setDownloadLoading({ type: "attributeSummary", loading: true }));
    const payload = {
      attribute: selectedAttributeTaxonset?.attribute,
      taxonSet: selectedAttributeTaxonset?.taxonset,
      asFile: true,
    };
    dispatchSuccessToast("Attribute Summary download has started");
    dispatch(getAttributeSummary(payload));

    setTimeout(
      () =>
        dispatch(
          setDownloadLoading({ type: "attributeSummary", loading: false })
        ),
      30000
    );
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
            onDownload={handleDownload}
          >
            <ClusterSizeDistribution />
          </ChartCard>
        </div>
      </div>
    </AppLayout>
  );
};

export default ClusterSizeDistributionPage;
