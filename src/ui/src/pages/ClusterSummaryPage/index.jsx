import React from "react";
import styles from "./ClusterSummary.module.scss";
import AppLayout from "../../components/AppLayout";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import AttributeSelector from "../../components/AttributeSelector";
import ClusterSummary from "../../components/Charts/ClusterSummary";

const ClusterSummaryPage = () => {
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
                <p className={styles.title}>Cluster Summary</p>
              </div>
              <ClusterSummary />
            </div>
          </div>
        </div>
      </AppLayout>
    </>
  );
};

export default ClusterSummaryPage;
