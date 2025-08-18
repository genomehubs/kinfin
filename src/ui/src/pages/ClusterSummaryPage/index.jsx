import React from "react";
import styles from "./ClusterSummary.module.scss";
import AppLayout from "../../components/AppLayout";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import { useDispatch, useSelector } from "react-redux";
import { getClusterSummary } from "../../app/store/analysis/slices/clusterSummarySlice";
import { dispatchSuccessToast } from "../../utils/tostNotifications";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";

const ClusterSummaryPage = () => {
  const dispatch = useDispatch();

  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset
  );
  const clusterSummaryDownloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading?.clusterSummary
  );

  const handleDownload = () => {
    dispatch(setDownloadLoading({ type: "clusterSummary", loading: true }));
    const payload = {
      attribute: selectedAttributeTaxonset?.attribute,
      taxonSet: selectedAttributeTaxonset?.taxonset,
      asFile: true,
    };

    dispatchSuccessToast("Cluster Summary download has started");
    dispatch(getClusterSummary(payload));

    // Fallback timeout to reset loading state
    setTimeout(() => {
      dispatch(setDownloadLoading({ type: "clusterSummary", loading: false }));
    }, 30000);
  };

  return (
    <AppLayout>
      <div className={styles.pageHeader}>
        <AttributeSelector />
      </div>
      <div className={styles.page}>
        <div className={styles.chartsContainer}>
          <ChartCard
            title="Cluster Summary"
            isDownloading={clusterSummaryDownloadLoading}
            onDownload={() => handleDownload("clusterSummary")}
          >
            <ClusterSummary />
          </ChartCard>
        </div>
      </div>
    </AppLayout>
  );
};

export default ClusterSummaryPage;
