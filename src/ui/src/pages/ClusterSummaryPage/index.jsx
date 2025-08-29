import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import CustomisationDialog from "../../components/CustomisationDialog";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { getClusterSummary } from "../../app/store/analysis/slices/clusterSummarySlice";
import { getColumnDescriptions } from "../../app/store/config/slices/columnDescriptionsSlice";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import styles from "./ClusterSummary.module.scss";
import { useSearchParams } from "react-router-dom";

const ClusterSummaryPage = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset
  );

  const clusterSummaryDownloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading?.clusterSummary
  );

  const columnDescriptions = useSelector((state) =>
    (state?.config?.columnDescriptions?.data || []).filter(
      (col) => col.file === "*.cluster_summary.txt"
    )
  );

  const [customiseOpen, setCustomiseOpen] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState([]);

  useEffect(() => {
    dispatch(getColumnDescriptions());
  }, []);

  useEffect(() => {
    const codes = searchParams.has("CS_code")
      ? searchParams.getAll("CS_code")
      : columnDescriptions
          .filter((col) => col.isDefault)
          .map((col) => col.code);
    if (JSON.stringify(codes) !== JSON.stringify(selectedCodes)) {
      setSelectedCodes(codes);
    }
  }, [searchParams, columnDescriptions]);

  const handleDownload = () => {
    dispatch(setDownloadLoading({ type: "clusterSummary", loading: true }));
    const payload = {
      attribute: selectedAttributeTaxonset?.attribute,
      taxonSet: selectedAttributeTaxonset?.taxonset,
      asFile: true,
    };
    dispatchSuccessToast("Cluster Summary download has started");
    dispatch(getClusterSummary(payload));

    setTimeout(() => {
      dispatch(setDownloadLoading({ type: "clusterSummary", loading: false }));
    }, 30000);
  };

  const handleCustomisation = () => {
    setCustomiseOpen(true);
  };

  const handleApply = (newSelectedCodes) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("CS_code");
    newSelectedCodes.forEach((c) => newParams.append("CS_code", c));
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
            title="Cluster Summary"
            isDownloading={clusterSummaryDownloadLoading}
            onDownload={handleDownload}
            onCustomise={handleCustomisation}
          >
            <ClusterSummary />
          </ChartCard>
        </div>
      </div>

      <CustomisationDialog
        open={customiseOpen}
        onClose={handleCancel}
        onApply={handleApply}
        selectedCodes={selectedCodes}
        columnDescriptions={columnDescriptions}
        title="Customise Cluster Summary"
      />
    </AppLayout>
  );
};

export default ClusterSummaryPage;
