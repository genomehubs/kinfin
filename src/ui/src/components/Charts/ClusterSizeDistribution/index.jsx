import React, { useEffect, useState } from "react";
import styles from "./ClusterSizeDistribution.module.scss";
import * as AnalysisActions from "../../../app/store/kinfin/actions";
import { useDispatch, useSelector } from "react-redux";

const ClusterSizeDistribution = () => {
  const dispatch = useDispatch();
  const clusterSizeBlob = useSelector(
    (state) => state?.analysis?.plot?.data?.clusterSizeDistribution
  );

  // Store blob URL in local state
  const [blobUrl, setBlobUrl] = useState(null);

  useEffect(() => {
    dispatch(AnalysisActions.getPlot());
  }, [dispatch]);

  useEffect(() => {
    console.log("🚀 clusterSizeBlob type:", clusterSizeBlob);

    if (clusterSizeBlob instanceof Blob) {
      const objectUrl = URL.createObjectURL(clusterSizeBlob);
      setBlobUrl(objectUrl);

      return () => {
        URL.revokeObjectURL(objectUrl); // Clean up
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

export default ClusterSizeDistribution;
