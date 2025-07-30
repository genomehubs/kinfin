import React from "react";
import styles from "./ClusterMetrics.module.scss";
import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";

const ClusterMetricsPage = () => {
  return (
    <>
      <AppLayout>
        <div className={styles.pageHeader}>
          <AttributeSelector />
        </div>
        <div className={styles.page}>
          <div className={styles.chartsContainer}>
            <div className={styles.container}>
              <div className={styles.header}>
                <p className={styles.title}>Cluster Metrics</p>
              </div>
              <ClusterMetrics />
            </div>
          </div>
        </div>
      </AppLayout>
    </>
  );
};

export default ClusterMetricsPage;
