import React, { useState } from "react";
import styles from "./dashboard.module.scss";
import { RunSummary } from "../../components";
// import ClusterSummary from "../../components/CLusterSummary";
import Modal from "../../components/UIElements/Modal";
import AttributeSelector from "../../components/AttributeSelector";
import CountsByTaxonChart from "../../components/Charts/CountsByTaxon";
import { useSelector } from "react-redux";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";

const Dashboard = () => {
  const [isModalOpen, setIsModalOpen] = useState(true);
  const countsByTaxonData = useSelector(
    (state) => state?.analysis?.countsByTaxon?.data
  );
  console.log("🚀 ~ Dashboard ~ countsByTaxonData:", countsByTaxonData);

  return (
    <div className={styles.page}>
      <AttributeSelector />
      <RunSummary />
      <div className={styles.chartsContainer}>
        <div className={styles.container}>
          <div className={styles.header}>
            <p className={styles.title}>Attribute Summary</p>
          </div>
          <div className={styles.chartContainer}>
            <AttributeSummary />
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.header}>
            <p className={styles.title}>Cluster Summary</p>
          </div>
          <div className={styles.chartContainer}>
            <ClusterSummary />
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.header}>
            <p className={styles.title}>Cluster Metrics</p>
          </div>
          <div className={styles.chartContainer}>
            <ClusterMetrics />
          </div>
        </div>
      </div>

      {/* <CountsByTaxonChart data={countsByTaxonData} /> */}
    </div>
  );
};

export default Dashboard;
