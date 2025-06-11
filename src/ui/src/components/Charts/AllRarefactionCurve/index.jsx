import React, { useEffect, useState } from "react";
import styles from "./AllRarefactionCurve.module.scss";
import { getPlot } from "../../../app/store/analysis/actions";
import { useDispatch, useSelector } from "react-redux";

const AllRarefactionCurve = () => {
  const dispatch = useDispatch();
  const clusterSizeBlob = useSelector(
    (state) => state?.analysis?.plot?.data?.allRarefactionCurve
  );

  const [blobUrl, setBlobUrl] = useState(null);

  useEffect(() => {
    dispatch(getPlot());
  }, [dispatch]);

  useEffect(() => {
    if (clusterSizeBlob instanceof Blob) {
      const objectUrl = URL.createObjectURL(clusterSizeBlob);
      setBlobUrl(objectUrl);

      return () => {
        URL.revokeObjectURL(objectUrl);
      };
    } else {
      console.error("❌ clusterSizeBlob is not a Blob:", clusterSizeBlob);
    }
  }, [clusterSizeBlob]);

  return (
    <div className={styles.container}>
      {blobUrl ? (
        <img
          className={styles.image}
          src={blobUrl}
          alt="Cluster Size Distribution"
          width="100%"
        />
      ) : (
        <p>Loading image...</p>
      )}
    </div>
  );
};

export default AllRarefactionCurve;
