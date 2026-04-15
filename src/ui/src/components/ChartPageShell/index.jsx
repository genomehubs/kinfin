import React, { useEffect } from "react";
import {
  getEffectiveColumnDescriptions,
  getSelectedAttributeTaxonset,
  makeSetSelectedAttributeTaxonset,
} from "./helpers";
import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../AppLayout";
import AttributeSelector from "../AttributeSelector";
import BaseChartPage from "../BaseChartPage";
import CustomisationDialog from "../CustomisationDialog";
import { handleDownload } from "../../utils/downloadHandlers";
import { setSelectedAttributeTaxonset as setSelectedAttributeTaxonsetAction } from "../../app/store/config/slices/uiStateSlice";
import styles from "./ChartPageShell.module.scss";
import useColumnDescriptions from "#hooks/useColumnDescriptions.js";
import useNavigateBack from "#hooks/useNavigateBack";
import usePageCustomisation from "#hooks/usePageCustomisation";
import { useSearchParams } from "react-router-dom";

const ALL_CODE_PARAMS = ["AS_code", "CS_code", "CM_code"];

const ChartPageShell = ({
  title,
  chartKey,
  columnDescriptions: columnDescriptionsProp,
  isDownloading = false,
  blob = null,
  searchParamKey,
  initialAttribute,
  initialTaxonset,
  setSelectedAttributeTaxonsetProp,
  renderChart,
}) => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  // Strip code params that don't belong to this page on mount
  useEffect(() => {
    const foreign = ALL_CODE_PARAMS.filter(
      (k) => k !== searchParamKey && searchParams.has(k),
    );
    if (foreign.length === 0) return;
    const newParams = new URLSearchParams(searchParams);
    foreign.forEach((k) => newParams.delete(k));
    setSearchParams(newParams, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: fetchedColumnDescriptions = [] } = useColumnDescriptions();

  const effectiveColumnDescriptions = getEffectiveColumnDescriptions(
    columnDescriptionsProp,
    fetchedColumnDescriptions,
  );

  const selectedFromStore = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset,
  );

  const { attribute, taxonset } = getSelectedAttributeTaxonset(
    selectedFromStore,
    initialAttribute,
    initialTaxonset,
  );

  const setSelectedAttributeTaxonset = makeSetSelectedAttributeTaxonset(
    dispatch,
    setSelectedAttributeTaxonsetProp,
    setSelectedAttributeTaxonsetAction,
  );

  const selectedAttributeTaxonset = { attribute, taxonset };

  const {
    selectedCodes,
    customiseOpen,
    openCustomise,
    handleApply,
    handleCancel,
  } = usePageCustomisation({
    searchParamKey,
    columnDescriptions: effectiveColumnDescriptions,
  });

  const goBack = useNavigateBack();
  const handleClose = () => goBack();

  const handleCustomisation = openCustomise;

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
          <BaseChartPage
            title={title}
            isDownloading={isDownloading}
            onDownload={() =>
              handleDownload({
                chartKey,
                dispatch,
                selectedAttributeTaxonset,
                blob,
              })
            }
            onCustomise={handleCustomisation}
            onClose={handleClose}
            customiseProps={{
              open: customiseOpen,
              onClose: handleCancel,
              onApply: handleApply,
              selectedCodes,
              columnDescriptions: effectiveColumnDescriptions,
              title: `Customise ${title}`,
            }}
          >
            {renderChart({
              attribute,
              taxonset,
              effectiveColumnDescriptions,
              selectedCodes,
              dispatch,
              setSelectedAttributeTaxonset,
            })}
          </BaseChartPage>
        </div>
      </div>

      <CustomisationDialog
        open={customiseOpen}
        onClose={handleCancel}
        onApply={handleApply}
        selectedCodes={selectedCodes}
        columnDescriptions={effectiveColumnDescriptions}
        title={`Customise ${title}`}
      />
    </AppLayout>
  );
};

export default ChartPageShell;
