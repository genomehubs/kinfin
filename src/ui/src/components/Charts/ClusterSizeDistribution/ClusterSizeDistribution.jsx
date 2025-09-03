import React, { useEffect, useState } from "react";

import { getPlot } from "../../../app/store/analysis/slices/plotSlice";
import styles from "./ClusterSizeDistribution.module.scss";
import { useDispatch } from "react-redux";

const ClusterSizeDistribution = ({
  attribute,
  clusterSizeDistributionBlob,
}) => {
  const dispatch = useDispatch();
  const [blobUrl, setBlobUrl] = useState(null);

  useEffect(() => {
    const payload = { attribute };
    dispatch(getPlot(payload));
  }, [dispatch, attribute]);

  useEffect(() => {
    if (clusterSizeDistributionBlob instanceof Blob) {
      const objectUrl = URL.createObjectURL(clusterSizeDistributionBlob);
      setBlobUrl(objectUrl);

      return () => {
        URL.revokeObjectURL(objectUrl);
      };
    }
  }, [clusterSizeDistributionBlob]);

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
