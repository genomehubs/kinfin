import React from "react";
import styles from "./RunSummary.module.scss";
import { useSelector } from "react-redux";

const RunSummary = () => {
  const data = useSelector((state) => state?.analysis?.runSummary?.data);

  const stats = [
    { label: "Total Clusters", value: data?.total_clusters },
    { label: "Total Proteins", value: data?.total_proteins },
    { label: "Total Proteomes", value: data?.total_proteomes },
    { label: "Filtered Clusters", value: data?.filtered_clusters },
    { label: "Filtered Proteins", value: data?.filtered_proteins },
    { label: "Included Proteins", value: data?.included_proteins_count },
    { label: "Excluded Proteins", value: data?.excluded_proteins_count },
  ];

  return (
    <>
      {/* <p>Run Summary</p> */}
      <div className={styles.container}>
        {stats.map((stat, index) => (
          <div key={index} className={styles.statContainer}>
            <p className={styles.data}>{stat.value ?? "N/A"}</p>
            <p className={styles.dataName}>{stat.label}</p>
          </div>
        ))}
      </div>
    </>
  );
};

export default RunSummary;
