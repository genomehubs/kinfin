import React, { useEffect, useState } from "react";
import styles from "./AttributeSummary.module.scss";
import AppLayout from "../../components/AppLayout";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import { useDispatch, useSelector } from "react-redux";
import { getAttributeSummary } from "../../app/store/analysis/slices/attributeSummarySlice";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import { useParams, useSearchParams } from "react-router-dom";
import CustomisationDialog from "../../components/CustomisationDialog";

import { getColumnDescriptions } from "../../app/store/config/slices/columnDescriptionsSlice";

const AttributeSummaryPage = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset
  );
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading
  );
  const { sessionId } = useParams();

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
    const paramsCodes = searchParams.getAll("AS_code");
    setSelectedCodes(paramsCodes);
  }, [searchParams]);

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

  const handleCheckboxChange = (code) => {
    setSelectedCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const handleApply = () => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("AS_code");
    selectedCodes.forEach((c) => newParams.append("AS_code", c));
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
        onCheckboxChange={handleCheckboxChange}
        columnDescriptions={columnDescriptions}
        title="Customise Attribute Summary"
        onSelectAll={() =>
          setSelectedCodes(columnDescriptions.map((c) => c.code))
        }
        onDeselectAll={() => setSelectedCodes([])}
      />
    </AppLayout>
  );
};

export default AttributeSummaryPage;
