import React, { useState, useEffect } from "react";
import styles from "./ClusterMetrics.module.scss";
import AppLayout from "../../components/AppLayout";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import { useDispatch, useSelector } from "react-redux";
import { getClusterMetrics } from "../../app/store/analysis/slices/clusterMetricsSlice";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import { useSearchParams } from "react-router-dom";
import CustomisationDialog from "../../components/CustomisationDialog";

import { getColumnDescriptions } from "../../app/store/config/slices/columnDescriptionsSlice";

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
    const paramsCodes = searchParams.getAll("CM_code");
    setSelectedCodes(paramsCodes);
  }, [searchParams]);

  useEffect(() => {
    dispatch(getColumnDescriptions());
  }, []);
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

  // Checkbox handler
  const handleCheckboxChange = (code) => {
    setSelectedCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  // Apply customisation
  const handleApply = () => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("CM_code");
    selectedCodes.forEach((c) => newParams.append("CM_code", c));
    setSearchParams(newParams);
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
        onCheckboxChange={handleCheckboxChange}
        columnDescriptions={columnDescriptions}
        title="Customise Cluster Metrics"
        onSelectAll={() =>
          setSelectedCodes(columnDescriptions.map((c) => c.code))
        }
        onDeselectAll={() => setSelectedCodes([])}
      />
    </AppLayout>
  );
};

export default ClusterMetricsPage;
