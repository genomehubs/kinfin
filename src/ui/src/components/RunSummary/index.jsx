import React, { useMemo } from "react";

import styles from "./RunSummary.module.scss";
import { useGetRunSummaryQuery } from "#store/api";

const RunSummary = () => {
  const { data: resp } = useGetRunSummaryQuery(undefined, {
    skip: false,
  });

  const stats = useMemo(() => {
    const data = resp?.data ?? resp ?? {};
    return [
      { label: "Total Clusters", value: data?.totalClusters },
      { label: "Total Proteins", value: data?.totalProteins },
      { label: "Total Proteomes", value: data?.totalProteomes },
      { label: "Filtered Clusters", value: data?.filteredClusters },
      { label: "Filtered Proteins", value: data?.filteredProteins },
      { label: "Included Proteins", value: data?.includedProteinsCount },
      { label: "Excluded Proteins", value: data?.excludedProteinsCount },
    ];
  }, [resp]);

  return (
    <div className={`${styles.container} ${styles.leftAlign}`}>
      {stats.map((stat, index) => (
        <div key={index} className={styles.statContainer}>
          <p
            className={`${styles.data} ${stat.value == null ? styles.noValue : ""}`}
          >
            {stat.value ?? "N/A"}
          </p>
          <p className={styles.dataName}>{stat.label}</p>
        </div>
      ))}
    </div>
  );
};

export default RunSummary;
