import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import RarefactionCurve from "../../components/Charts/RarefactionCurve";
import React from "react";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { getAttributeSummary } from "../../app/store/analysis/slices/attributeSummarySlice";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import styles from "./RarefactionCurve.module.scss";

const RarefactionCurvePage = () => {
  const dispatch = useDispatch();
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset
  );
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading
  );

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
            title="Rarefaction Curve"
            isDownloading={downloadLoading?.downloadLoading?.rareFactionCurve}
            onDownload={handleDownload}
            onClose={handleClose}
          >
            <RarefactionCurve />
          </ChartCard>
        </div>
      </div>
    </AppLayout>
  );
};

export default RarefactionCurvePage;
