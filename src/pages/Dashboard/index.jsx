import React, { useState, useEffect } from "react";
import styles from "./dashboard.module.scss";
import * as AnalysisActions from "../../app/store/kinfin/actions";

import { RunSummary } from "../../components";
import Modal from "../../components/UIElements/Modal";
import AttributeSelector from "../../components/AttributeSelector";
import { useDispatch, useSelector } from "react-redux";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import ClusterAndProteinDistributionPerTaxonSet from "../../components/Charts/ClusterAndProteinDistributionPerTaxonSet";
import ClusterAbsenceAcrossTaxonSets from "../../components/Charts/ClusterAbsenceAcrossTaxonSets";
import TaxonCountPerTaxonSet from "../../components/Charts/TaxonCountPerTaxonSet";
import { IoOpenOutline } from "react-icons/io5";

const Dashboard = () => {
  const [enlargedChart, setEnlargedChart] = useState(null);
  const dispatch = useDispatch();

  const selectedAttributeTaxonset = useSelector(
    (state) => state?.analysis?.selectedAttributeTaxonset
  );

  useEffect(() => {
    dispatch(AnalysisActions.getRunStatus());
    dispatch(AnalysisActions.getAvailableAttributesTaxonsets());
    dispatch(AnalysisActions.getRunSummary());
    dispatch(AnalysisActions.getCountsByTaxon());
    dispatch(
      AnalysisActions.getClusterSummary({
        attribute: selectedAttributeTaxonset?.attribute,
      })
    );
    dispatch(
      AnalysisActions.getAttributeSummary({
        attribute: selectedAttributeTaxonset?.attribute,
      })
    );
    dispatch(
      AnalysisActions.getClusterMetrics({
        attribute: selectedAttributeTaxonset?.attribute,
        taxonSet: selectedAttributeTaxonset?.taxonset,
      })
    );
  }, [dispatch, selectedAttributeTaxonset]);

  const handleEnlarge = (chartName) => setEnlargedChart(chartName);

  const closeModal = () => setEnlargedChart(null);

  const modalTitleMap = {
    attributeSummary: "Attribute Summary",
    clusterSummary: "Cluster Summary",
    clusterMetrics: "Cluster Metrics",
    clusterAndProteinDistribution: "Cluster Distribution Per Taxon",
    clusterAbsence: "Cluster Absence Across Taxon Sets",
    taxonCount: "Taxon Count per Taxon Set",
  };

  const renderModalContent = () => {
    switch (enlargedChart) {
      case "attributeSummary":
        return <AttributeSummary />;
      case "clusterSummary":
        return <ClusterSummary />;
      case "clusterMetrics":
        return <ClusterMetrics />;
      case "clusterAndProteinDistribution":
        return <ClusterAndProteinDistributionPerTaxonSet />;
      case "clusterAbsence":
        return <ClusterAbsenceAcrossTaxonSets />;
      case "taxonCount":
        return <TaxonCountPerTaxonSet />;
      default:
        return null;
    }
  };

  const renderDashboardChart = (chartKey) => {
    switch (chartKey) {
      case "attributeSummary":
        return <AttributeSummary />;
      case "clusterSummary":
        return <ClusterSummary />;
      case "clusterMetrics":
        return <ClusterMetrics />;
      case "clusterAndProteinDistribution":
        return <ClusterAndProteinDistributionPerTaxonSet />;
      case "clusterAbsence":
        return <ClusterAbsenceAcrossTaxonSets />;
      case "taxonCount":
        return <TaxonCountPerTaxonSet />;
      default:
        return null;
    }
  };

  return (
    <>
      <Modal
        isOpen={!!enlargedChart}
        onClose={closeModal}
        title={modalTitleMap[enlargedChart] || ""}
      >
        {renderModalContent()}
      </Modal>

      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>KinFin Analysis</h1>
        <AttributeSelector />
      </div>

      <div className={styles.page}>
        <RunSummary />
        <div className={styles.chartsContainer}>
          {Object.entries(modalTitleMap).map(([key, label]) => (
            <div key={key} className={styles.container}>
              <div className={styles.header}>
                <button
                  className={styles.enlargeButton}
                  onClick={() => handleEnlarge(key)}
                >
                  <IoOpenOutline />
                </button>
                <p className={styles.title}>{label}</p>
              </div>
              <div className={styles.chartContainer}>
                {renderDashboardChart(key)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

export default Dashboard;
