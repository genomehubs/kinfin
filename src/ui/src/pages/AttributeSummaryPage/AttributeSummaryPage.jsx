import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import ChartCard from "../../components/ChartCard";
import CustomisationDialog from "../../components/CustomisationDialog";
import { getColumnDescriptions } from "../../app/store/config/slices/columnDescriptionsSlice";
import { handleDownload } from "../../utils/downloadHandlers";
import styles from "./AttributeSummary.module.scss";
import { useSearchParams } from "react-router-dom";

const AttributeSummaryPage = ({
  selectedAttributeTaxonset,
  attributeSummaryColumnDescriptions: columnDescriptions,
}) => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  // useEffect(() => {
  //   dispatch(getColumnDescriptions());
  //   // eslint-disable-next-line react-hooks/exhaustive-deps
  // }, []);

  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading
  );

  const [customiseOpen, setCustomiseOpen] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState([]);

  useEffect(() => {
    dispatch(getColumnDescriptions());
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, columnDescriptions]);

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

  const handleClose = () => {
    window.history.back();
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
            onDownload={() =>
              handleDownload({
                chartKey: "attributeSummary",
                dispatch,
                selectedAttributeTaxonset,
              })
            }
            onCustomise={handleCustomisation}
            onClose={handleClose}
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
