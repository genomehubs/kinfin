import React from "react";
import styles from "./AttributeSummary.module.scss";
import AppLayout from "../../components/AppLayout";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import AttributeSelector from "../../components/AttributeSelector";

const AttributeSummaryPage = () => {
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
                <p className={styles.title}>Attribute Summary</p>
              </div>
              <AttributeSummary />
            </div>
          </div>
        </div>
      </AppLayout>
    </>
  );
};

export default AttributeSummaryPage;
