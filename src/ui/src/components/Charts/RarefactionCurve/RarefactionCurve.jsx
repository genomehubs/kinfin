import React, { useEffect, useState } from "react";

import styles from "./RarefactionCurve.module.scss";
import usePlot from "#hooks/usePlot";

const RarefactionCurve = ({ attribute }) => {
  const {
    data: rarefactionCurveBlob,
    isFetching,
    error,
  } = usePlot(
    { attribute, plotType: "rarefaction-curve" },
    { skip: !attribute },
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
