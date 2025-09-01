import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { getPlot } from "../../../app/store/analysis/slices/plotSlice";
import styles from "./ClusterSizeDistribution.module.scss";

const ClusterSizeDistribution = ({ attribute }) => {
  const dispatch = useDispatch();
  const clusterSizeBlob = useSelector(
    (state) => state?.analysis?.plot?.data?.clusterSizeDistribution
  );

  const [blobUrl, setBlobUrl] = useState(null);

  useEffect(() => {
    const payload = { attribute };
    dispatch(getPlot(payload));
  }, [dispatch, attribute]);

  useEffect(() => {
    if (clusterSizeBlob instanceof Blob) {
      const objectUrl = URL.createObjectURL(clusterSizeBlob);
      setBlobUrl(objectUrl);

      return () => {
        URL.revokeObjectURL(objectUrl);
      };
      // } else {
      //   console.error("❌ clusterSizeBlob is not a Blob:", clusterSizeBlob);
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
