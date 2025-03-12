import React, { useState } from "react";
import styles from "./dashboard.module.scss";
import { RunSummary } from "../../components";
import ClusterSummary from "../../components/CLusterSummary";
import Modal from "../../components/UIElements/Modal";
import AttributeSelector from "../../components/AttributeSelector";
import CountsByTaxonChart from "../../components/Charts/CountsByTaxon";
import { useSelector } from "react-redux";

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
      {/* <ClusterSummary /> */}

      {/* <CountsByTaxonChart data={countsByTaxonData} /> */}
    </div>
  );
};

export default Dashboard;
