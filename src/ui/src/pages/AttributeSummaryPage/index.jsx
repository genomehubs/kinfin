import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import ChartCard from "../../components/ChartCard";
import CustomisationDialog from "../../components/CustomisationDialog";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { getAttributeSummary } from "../../app/store/analysis/slices/attributeSummarySlice";
import { getColumnDescriptions } from "../../app/store/config/slices/columnDescriptionsSlice";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import styles from "./AttributeSummary.module.scss";
import { useSearchParams } from "react-router-dom";

const AttributeSummaryPage = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset
  );

  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading
  );

  const columnDescriptions = useSelector((state) =>
    (state?.config?.columnDescriptions?.data || []).filter(
      (col) => col.file === "*.attribute_metrics.txt"
    )
  );

  const [customiseOpen, setCustomiseOpen] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState([]);

  useEffect(() => {
    dispatch(getColumnDescriptions());
  }, []);

  useEffect(() => {
    const codes = searchParams.has("AS_code")
      ? searchParams.getAll("AS_code")
      : columnDescriptions
          .filter((col) => col.isDefault)
          .map((col) => col.code);
    if (JSON.stringify(codes) !== JSON.stringify(selectedCodes)) {
      setSelectedCodes(codes);
    }
  }, [searchParams, columnDescriptions]);

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

  const handleCustomisation = () => {
    setCustomiseOpen(true);
  };

  const handleApply = (newSelectedCodes) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("AS_code");
    newSelectedCodes.forEach((c) => newParams.append("AS_code", c));
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
            title="Attribute Summary"
            isDownloading={downloadLoading?.downloadLoading?.attributeSummary}
            onDownload={handleDownload}
            onCustomise={handleCustomisation}
          >
            <AttributeSummary />
          </ChartCard>
        </div>
      </div>

      <CustomisationDialog
        open={customiseOpen}
        onClose={handleCancel}
        onApply={handleApply}
        selectedCodes={selectedCodes}
        columnDescriptions={columnDescriptions}
        title="Customise Attribute Summary"
      />
    </AppLayout>
  );
};

export default AttributeSummaryPage;
