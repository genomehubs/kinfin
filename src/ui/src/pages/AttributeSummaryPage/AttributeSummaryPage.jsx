import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import ChartCard from "../../components/ChartCard";
import CustomisationDialog from "../../components/CustomisationDialog";
import { handleDownload } from "../../utils/downloadHandlers";
import styles from "./AttributeSummary.module.scss";
import useColumnDescriptions from "#hooks/useColumnDescriptions.js";
import { useSearchParams } from "react-router-dom";
import useNavigateBack from "#hooks/useNavigateBack";
import { setSelectedAttributeTaxonset as setSelectedAttributeTaxonsetAction } from "../../app/store/config/slices/uiStateSlice";

const AttributeSummaryPage = ({
  // selectedAttributeTaxonset: _selectedAttributeTaxonset,
  attributeSummaryColumnDescriptions: columnDescriptions,
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();
  // ensure column descriptions are fetched via RTK Query
  const { data: fetchedColumnDescriptions = [] } = useColumnDescriptions();

  const effectiveColumnDescriptions =
    columnDescriptions && columnDescriptions.length
      ? columnDescriptions
      : fetchedColumnDescriptions;

  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading,
  );

  const [customiseOpen, setCustomiseOpen] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState([]);

  // If the container HOC is not used, read selectedAttributeTaxonset from redux
  const selectedFromStore = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset,
  );

  const attribute = propAttribute ?? selectedFromStore?.attribute ?? "all";
  const taxonset = propTaxonset ?? selectedFromStore?.taxonset ?? "all";

  const setSelectedAttributeTaxonset =
    propSetSelectedAttributeTaxonset ??
    ((payload) => dispatch(setSelectedAttributeTaxonsetAction(payload)));

  useEffect(() => {
    const codes = searchParams.has("AS_code")
      ? searchParams.getAll("AS_code")
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
    newParams.delete("AS_code");
    newSelectedCodes.forEach((c) => newParams.append("AS_code", c));
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
            <AttributeSummary
              attribute={attribute}
              attributeSummaryColumnDescriptions={effectiveColumnDescriptions}
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
        title="Customise Attribute Summary"
      />
    </AppLayout>
  );
};

export default AttributeSummaryPage;
