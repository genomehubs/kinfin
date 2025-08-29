import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { getPlot } from "../../../app/store/analysis/slices/plotSlice";
import styles from "./RarefactionCurve.module.scss";
import { useSearchParams } from "react-router-dom";

const RarefactionCurve = () => {
  const dispatch = useDispatch();
  const [searchParams] = useSearchParams();
  const rarefactionCurveBlob = useSelector(
    (state) => state?.analysis?.plot?.data?.rarefactionCurve
  );

  const [blobUrl, setBlobUrl] = useState(null);

  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset || null
  );
  const attribute =
    selectedAttributeTaxonset?.attribute ||
    searchParams.get("attribute") ||
    "all";

  useEffect(() => {
    const payload = { attribute };
    dispatch(getPlot(payload));
  }, [dispatch, attribute]);

  useEffect(() => {
    if (rarefactionCurveBlob instanceof Blob) {
      const objectUrl = URL.createObjectURL(rarefactionCurveBlob);
      setBlobUrl(objectUrl);

      return () => {
        URL.revokeObjectURL(objectUrl);
      };
      // } else {
      //   console.error(
      //     "❌ rarefactionCurveBlob is not a Blob:",
      //     rarefactionCurveBlob
      //   );
    }
  }, [rarefactionCurveBlob]);

  return (
    <div className={styles.container}>
      {blobUrl ? (
        <img
          src={blobUrl}
          alt="Cluster Size Distribution"
          className={styles.image}
        />
      ) : (
        <p>Loading image...</p>
      )}
    </div>
  );
};

export default RarefactionCurve;
