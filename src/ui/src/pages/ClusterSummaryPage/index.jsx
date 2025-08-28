import React, { useEffect, useState } from "react";
import styles from "./ClusterSummary.module.scss";
import AppLayout from "../../components/AppLayout";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import { useDispatch, useSelector } from "react-redux";
import { getClusterSummary } from "../../app/store/analysis/slices/clusterSummarySlice";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import { useSearchParams } from "react-router-dom";
import { getColumnDescriptions } from "../../app/store/config/slices/columnDescriptionsSlice";
import CustomisationDialog from "../../components/CustomisationDialog";

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

  // Load selected codes from URL
  useEffect(() => {
    const paramsCodes = searchParams.getAll("CS_code");
    setSelectedCodes(paramsCodes);
  }, [searchParams]);
  useEffect(() => {
    dispatch(getColumnDescriptions());
  }, []);
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

  const handleCheckboxChange = (code) => {
    setSelectedCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const handleApply = () => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("CS_code");
    selectedCodes.forEach((c) => newParams.append("CS_code", c));
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
        onCheckboxChange={handleCheckboxChange}
        columnDescriptions={columnDescriptions}
        title="Customise Cluster Summary"
        onSelectAll={() =>
          setSelectedCodes(columnDescriptions.map((c) => c.code))
        }
        onDeselectAll={() => setSelectedCodes([])}
      />
    </AppLayout>
  );
};

export default ClusterSummaryPage;
