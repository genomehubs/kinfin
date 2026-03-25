import { useDispatch, useSelector } from "react-redux";

import AppLayout from "#components/AppLayout";
import AttributeSelector from "#components/AttributeSelector";
import ChartCard from "#components/ChartCard";
import RarefactionCurve from "#components/Charts/RarefactionCurve";
import React from "react";
import { handleDownload } from "#utils/downloadHandlers";
import useNavigateBack from "#hooks/useNavigateBack";
import { setSelectedAttributeTaxonset as setSelectedAttributeTaxonsetAction } from "../../app/store/config/slices/uiStateSlice";
import styles from "./RarefactionCurve.module.scss";

const RarefactionCurvePage = ({
  // selectedAttributeTaxonset: _selectedAttributeTaxonset,
  rarefactionCurveBlob,
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  const dispatch = useDispatch();
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading,
  );

  const goBack = useNavigateBack();
  const handleClose = () => goBack();

  const selectedFromStore = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset,
  );

  const attribute = propAttribute ?? selectedFromStore?.attribute ?? "all";
  const taxonset = propTaxonset ?? selectedFromStore?.taxonset ?? "all";

  const setSelectedAttributeTaxonset =
    propSetSelectedAttributeTaxonset ??
    ((payload) => dispatch(setSelectedAttributeTaxonsetAction(payload)));

  const effectiveSelected = { attribute, taxonset };

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
            title="Rarefaction Curve"
            isDownloading={downloadLoading?.downloadLoading?.rarefactionCurve}
            onDownload={() =>
              handleDownload({
                chartKey: "rarefaction-curve",
                dispatch,
                selectedAttributeTaxonset: effectiveSelected,
                rarefactionCurveBlob,
              })
            }
            onClose={handleClose}
          >
            <RarefactionCurve attribute={attribute} />
          </ChartCard>
        </div>
      </div>
    </AppLayout>
  );
};

export default RarefactionCurvePage;
