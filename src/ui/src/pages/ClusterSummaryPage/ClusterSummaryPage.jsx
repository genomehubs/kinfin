import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import AppLayout from "#components/AppLayout";
import AttributeSelector from "#components/AttributeSelector";
import ChartCard from "#components/ChartCard";
import ClusterSummary from "#components/Charts/ClusterSummary";
import CustomisationDialog from "#components/CustomisationDialog";
import { handleDownload } from "#utils/downloadHandlers";
import styles from "./ClusterSummary.module.scss";
import useColumnDescriptions from "#hooks/useColumnDescriptions.js";
import { useSearchParams } from "react-router-dom";

const ClusterSummaryPage = ({
  // selectedAttributeTaxonset: _selectedAttributeTaxonset,
  clusterSummaryColumnDescriptions: columnDescriptions,
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  const { data: fetchedColumnDescriptions = [] } = useColumnDescriptions();
  const [searchParams, setSearchParams] = useSearchParams();
  const dispatch = useDispatch();

  const clusterSummaryDownloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading?.clusterSummary,
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
    ((payload) =>
      dispatch({ type: "uiState/setSelectedAttributeTaxonset", payload }));

  // If `columnDescriptions` prop isn't provided, fall back to fetched data
  const effectiveColumnDescriptions =
    columnDescriptions && columnDescriptions.length
      ? columnDescriptions
      : fetchedColumnDescriptions;

  useEffect(() => {
    const codes = searchParams.has("CS_code")
      ? searchParams.getAll("CS_code")
      : effectiveColumnDescriptions
          .filter((col) => col.isDefault)
          .map((col) => col.code);
    if (JSON.stringify(codes) !== JSON.stringify(selectedCodes)) {
      setSelectedCodes(codes);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, columnDescriptions]);

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

  const handleClose = () => {
    window.history.back();
  };

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
            title="Cluster Summary"
            isDownloading={clusterSummaryDownloadLoading}
            onDownload={() =>
              handleDownload({
                chartKey: "clusterSummary",
                dispatch,
                selectedAttributeTaxonset,
              })
            }
            onCustomise={handleCustomisation}
            onClose={handleClose}
          >
            <ClusterSummary
              attribute={attribute}
              clusterSummaryColumnDescriptions={effectiveColumnDescriptions}
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
        title="Customise Cluster Summary"
      />
    </AppLayout>
  );
};

export default ClusterSummaryPage;
