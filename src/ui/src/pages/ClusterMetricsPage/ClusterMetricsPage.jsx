import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import CustomisationDialog from "../../components/CustomisationDialog";
import { handleDownload } from "../../utils/downloadHandlers";
import styles from "./ClusterMetrics.module.scss";
import useColumnDescriptions from "#hooks/useColumnDescriptions.js";
import { useSearchParams } from "react-router-dom";
import useNavigateBack from "#hooks/useNavigateBack";
import { setSelectedAttributeTaxonset as setSelectedAttributeTaxonsetAction } from "../../app/store/config/slices/uiStateSlice";

const ClusterMetricsPage = ({
  // selectedAttributeTaxonset: _selectedAttributeTaxonset,
  clusterMetricsColumnDescriptions: columnDescriptions,
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const clusterMetricsDownloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading?.clusterMetrics,
  );

  const [customiseOpen, setCustomiseOpen] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState([]);

  const selectedFromStore = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset,
  );

  const attribute = propAttribute ?? selectedFromStore?.attribute ?? "all";
  const taxonset = propTaxonset ?? selectedFromStore?.taxonset ?? "all";

  const setSelectedAttributeTaxonset =
    propSetSelectedAttributeTaxonset ??
    ((payload) => dispatch(setSelectedAttributeTaxonsetAction(payload)));

  // fetch column descriptions via RTK Query hook
  const { data: fetchedColumnDescriptions = [] } = useColumnDescriptions();

  const effectiveColumnDescriptions =
    columnDescriptions && columnDescriptions.length
      ? columnDescriptions
      : fetchedColumnDescriptions;

  useEffect(() => {
    const codes = searchParams.has("CM_code")
      ? searchParams.getAll("CM_code")
      : effectiveColumnDescriptions
          .filter((col) => col.isDefault)
          .map((col) => col.code);
    if (JSON.stringify(codes) !== JSON.stringify(selectedCodes)) {
      setSelectedCodes(codes);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, columnDescriptions]);

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

  const goBack = useNavigateBack();
  const handleClose = () => goBack();

  const selectedAttributeTaxonset = { attribute, taxonset };

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
            title="Cluster Metrics"
            isDownloading={clusterMetricsDownloadLoading}
            onDownload={() =>
              handleDownload({
                chartKey: "clusterMetrics",
                dispatch,
                selectedAttributeTaxonset,
              })
            }
            onCustomise={handleCustomisation}
            onClose={handleClose}
          >
            <ClusterMetrics
              attribute={attribute}
              taxonset={taxonset}
              clusterMetricsColumnDescriptions={effectiveColumnDescriptions}
            />
          </ChartCard>
        </div>
      </div>

      <CustomisationDialog
        open={customiseOpen}
        onClose={handleCancel}
        onApply={handleApply}
        selectedCodes={selectedCodes}
        columnDescriptions={effectiveColumnDescriptions}
        title="Customise Cluster Metrics"
      />
    </AppLayout>
  );
};

export default ClusterMetricsPage;
