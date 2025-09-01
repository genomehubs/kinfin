import { useDispatch, useSelector } from "react-redux";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import RarefactionCurve from "../../components/Charts/RarefactionCurve";
import React from "react";
import { handleDownload } from "../../utils/downloadHandlers";
import styles from "./RarefactionCurve.module.scss";

const RarefactionCurvePage = ({
  selectedAttributeTaxonset,
  rarefactionCurveBlob,
}) => {
  const dispatch = useDispatch();
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading
  );

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
            onDownload={() =>
              handleDownload({
                chartKey: "rarefactionCurve",
                dispatch,
                selectedAttributeTaxonset,
                rarefactionCurveBlob,
              })
            }
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
