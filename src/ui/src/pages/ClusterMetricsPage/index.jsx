import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import CustomisationDialog from "../../components/CustomisationDialog";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { getClusterMetrics } from "../../app/store/analysis/slices/clusterMetricsSlice";
import { getColumnDescriptions } from "../../app/store/config/slices/columnDescriptionsSlice";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import styles from "./ClusterMetrics.module.scss";
import { useSearchParams } from "react-router-dom";

const ClusterMetricsPage = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset
  );

  const clusterMetricsDownloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading?.clusterMetrics
  );

  const columnDescriptions = useSelector((state) =>
    (state?.config?.columnDescriptions?.data || []).filter(
      (col) => col.file === "*.cluster_metrics.txt"
    )
  );

  const [customiseOpen, setCustomiseOpen] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState([]);

  useEffect(() => {
    dispatch(getColumnDescriptions());
  }, []);

  useEffect(() => {
    const codes = searchParams.has("CM_code")
      ? searchParams.getAll("CM_code")
      : columnDescriptions
          .filter((col) => col.isDefault)
          .map((col) => col.code);
    if (JSON.stringify(codes) !== JSON.stringify(selectedCodes)) {
      setSelectedCodes(codes);
    }
  }, [searchParams, columnDescriptions]);

  // Download handler
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

  // Open customisation modal
  const handleCustomisation = () => {
    setCustomiseOpen(true);
  };

  // Apply customisation
  const handleApply = (newSelectedCodes) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("CM_code");
    newSelectedCodes.forEach((c) => newParams.append("CM_code", c));
    setSearchParams(newParams);
    setSelectedCodes(newSelectedCodes);
    setCustomiseOpen(false);
  };

  const handleCancel = () => {
    setCustomiseOpen(false);
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
            onCustomise={handleCustomisation}
          >
            <ClusterMetrics />
          </ChartCard>
        </div>
      </div>

      <CustomisationDialog
        open={customiseOpen}
        onClose={handleCancel}
        onApply={handleApply}
        selectedCodes={selectedCodes}
        columnDescriptions={columnDescriptions}
        title="Customise Cluster Metrics"
      />
    </AppLayout>
  );
};

export default ClusterMetricsPage;
