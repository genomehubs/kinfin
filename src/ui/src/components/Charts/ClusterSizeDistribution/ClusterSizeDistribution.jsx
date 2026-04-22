import React, { useEffect, useState } from "react";

import { getSessionId } from "@/app/utils/session";
import styles from "./ClusterSizeDistribution.module.scss";
import { useGetPlotQuery } from "#store/api";
import { useParams } from "react-router-dom";

const ClusterSizeDistribution = ({
  attribute,
  clusterSizeDistributionBlob,
}) => {
  const { sessionId: sessionIdFromParams } = useParams();
  const sessionId = sessionIdFromParams || getSessionId();

  const [blobUrl, setBlobUrl] = useState(null);
  const [createdObjectUrl, setCreatedObjectUrl] = useState(false);

  const {
    data: plotBlob,
    isFetching,
    error,
  } = useGetPlotQuery(
    { attribute, plotType: "cluster-size-distribution", sessionId },
    { skip: !attribute, refetchOnMountOrArgChange: true },
  );

  // The API layer converts blob responses into a serializable wrapper:
  // { __isBlob: true, url, size, type }
  // Consumers should accept that shape, raw Blob, or a pre-existing URL.
  const effectivePlotBlob = plotBlob ?? clusterSizeDistributionBlob;

  useEffect(() => {
    // Clean up any previously created object URL
    return () => {
      if (createdObjectUrl && blobUrl) {
        try {
          URL.revokeObjectURL(blobUrl);
        } catch (e) {
          // ignore
        }
      }
    };
  }, [createdObjectUrl, blobUrl]);

  useEffect(() => {
    if (!effectivePlotBlob) {
      setBlobUrl(null);
      setCreatedObjectUrl(false);
      return;
    }

    // If the wrapper produced by the base query is present, use its URL directly
    if (
      effectivePlotBlob.__isBlob &&
      typeof effectivePlotBlob.url === "string"
    ) {
      // wrapper URL is managed by the browser; do not revoke it here
      setBlobUrl(effectivePlotBlob.url);
      setCreatedObjectUrl(false);
      return;
    }

    // If we already have a string URL (fallback), use it directly
    if (typeof effectivePlotBlob === "string") {
      setBlobUrl(effectivePlotBlob);
      setCreatedObjectUrl(false);
      return;
    }

    // If it's a raw Blob, create an object URL and remember to revoke it
    if (effectivePlotBlob instanceof Blob) {
      const objectUrl = URL.createObjectURL(effectivePlotBlob);
      setBlobUrl(objectUrl);
      setCreatedObjectUrl(true);
      return;
    }

    // Unknown shape: clear
    setBlobUrl(null);
    setCreatedObjectUrl(false);
  }, [effectivePlotBlob]);

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
