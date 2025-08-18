import React from "react";
import styles from "./ClusterMetrics.module.scss";
import AppLayout from "../../components/AppLayout";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import { useDispatch, useSelector } from "react-redux";
import { getClusterMetrics } from "../../app/store/analysis/slices/clusterMetricsSlice";
import { dispatchSuccessToast } from "../../utilis/tostNotifications";
import { setDownloadLoading } from "../../app/store/config/actions";

const ClusterMetricsPage = () => {
  const dispatch = useDispatch();
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.selectedAttributeTaxonset
  );
  const clusterMetricsDownloadLoading = useSelector(
    (state) => state?.config?.downloadLoading?.clusterMetrics
  );

  const handleDownload = () => {
    dispatch(setDownloadLoading({ type: "clusterMetrics", loading: true }));
    const payload = {
      attribute: selectedAttributeTaxonset?.attribute,
      taxonSet: selectedAttributeTaxonset?.taxonset,
      asFile: true,
    };
    dispatchSuccessToast("Cluster Metrics download has started");
    dispatch(getClusterMetrics(payload));
    setTimeout(
      () =>
        dispatch(
          setDownloadLoading({ type: "clusterMetrics", loading: false })
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
            title="Cluster Metrics"
            isDownloading={clusterMetricsDownloadLoading}
            onDownload={handleDownload}
          >
            <ClusterMetrics />
          </ChartCard>
        </div>
      </div>
    </AppLayout>
  );
};

export default ClusterMetricsPage;
