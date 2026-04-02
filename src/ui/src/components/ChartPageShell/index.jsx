import React from "react";
import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../AppLayout";
import AttributeSelector from "../AttributeSelector";
import BaseChartPage from "../BaseChartPage";
import CustomisationDialog from "../CustomisationDialog";
import { handleDownload } from "../../utils/downloadHandlers";
import styles from "./ChartPageShell.module.scss";
import useColumnDescriptions from "#hooks/useColumnDescriptions.js";
import usePageCustomisation from "#hooks/usePageCustomisation";
import useNavigateBack from "#hooks/useNavigateBack";
import { setSelectedAttributeTaxonset as setSelectedAttributeTaxonsetAction } from "../../app/store/config/slices/uiStateSlice";
import {
  getEffectiveColumnDescriptions,
  getSelectedAttributeTaxonset,
  makeSetSelectedAttributeTaxonset,
} from "./helpers";

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
