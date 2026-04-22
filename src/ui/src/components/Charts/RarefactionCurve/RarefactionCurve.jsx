import React, { useEffect, useState } from "react";

import { getSessionId } from "@/app/utils/session";
import styles from "./RarefactionCurve.module.scss";
import { useParams } from "react-router-dom";
import usePlot from "#hooks/usePlot";

const RarefactionCurve = ({ attribute }) => {
  const { sessionId: sessionIdFromParams } = useParams();
  const sessionId = sessionIdFromParams || getSessionId();

  const {
    data: rarefactionCurveBlob,
    isFetching,
    error,
  } = usePlot(
    { attribute, plotType: "rarefaction-curve", sessionId },
    { skip: !attribute, refetchOnMountOrArgChange: true },
  );

  const [blobUrl, setBlobUrl] = useState(null);

  const effectiveRarefactionBlob =
    rarefactionCurveBlob?.data ?? rarefactionCurveBlob;

  useEffect(() => {
    const blob = effectiveRarefactionBlob;
    if (blob instanceof Blob) {
      const objectUrl = URL.createObjectURL(blob);
      setBlobUrl(objectUrl);
      return () => URL.revokeObjectURL(objectUrl);
    } else if (blob && typeof blob.url === "string") {
      // The plot hook returned an object wrapping a Blob-like resource
      // which already contains a usable `url` (e.g. created elsewhere).
      setBlobUrl(blob.url);
    } else {
      setBlobUrl(null);
    }
  }, [effectiveRarefactionBlob]);

  if (isFetching) return <p>Loading image...</p>;
  if (error) return <p style={{ color: "red" }}>Error loading image</p>;

  return (
    <div className={styles.container}>
      {blobUrl ? (
        <img src={blobUrl} alt="Rarefaction Curve" className={styles.image} />
      ) : (
        <p>No image available</p>
      )}
    </div>
  );
};

export default RarefactionCurve;
