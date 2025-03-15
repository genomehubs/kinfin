import React, { useState, useEffect } from "react";
import styles from "./dashboard.module.scss";
import * as AnalysisActions from "../../app/store/kinfin/actions";

import { RunSummary } from "../../components";
// import ClusterSummary from "../../components/CLusterSummary";
import Modal from "../../components/UIElements/Modal";
import AttributeSelector from "../../components/AttributeSelector";
import CountsByTaxonChart from "../../components/Charts/CountsByTaxon";
import { useDispatch, useSelector } from "react-redux";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import ClusterSizeDistribution from "../../components/Charts/ClusterSizeDistribution";
import AllRarefactionCurve from "../../components/Charts/AllRarefactionCurve";
import ClusterAndProteinDistributionPerTaxonSet from "../../components/Charts/ClusterAndProteinDistributionPerTaxonSet";
import ClusterAbsenceAcrossTaxonSets from "../../components/Charts/ClusterAbsenceAcrossTaxonSets";
import TaxonCountPerTaxonSet from "../../components/Charts/TaxonCountPerTaxonSet";

const Dashboard = () => {
  const [isModalOpen, setIsModalOpen] = useState(true);
  const dispatch = useDispatch();
  const countsByTaxonData = useSelector(
    (state) => state?.analysis?.countsByTaxon?.data
  );
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
  console.log("🚀 ~ Dashboard ~ countsByTaxonData:", countsByTaxonData);

  return (
    <div className={styles.page}>
      <h1>KinFin Analysis</h1>
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
        <div className={styles.container}>
          <div className={styles.header}>
            <p className={styles.title}>Cluster Size Distribution</p>
          </div>
          <div className={styles.chartContainer}>
            <ClusterSizeDistribution />
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.header}>
            <p className={styles.title}>All Rarefaction Curve</p>
          </div>
          <div className={styles.chartContainer}>
            <AllRarefactionCurve />
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.header}>
            <p className={styles.title}>Cluster Distribution Per Taxon</p>
          </div>
          <div className={styles.chartContainer}>
            <ClusterAndProteinDistributionPerTaxonSet />
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.header}>
            <p className={styles.title}>Cluster Absence Across Taxon Sets</p>
          </div>
          <div className={styles.chartContainer}>
            <ClusterAbsenceAcrossTaxonSets />
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.header}>
            <p className={styles.title}>Taxon Count per Taxon Set</p>
          </div>
          <div className={styles.chartContainer}>
            <TaxonCountPerTaxonSet />
          </div>
        </div>
      </div>

      {/* <CountsByTaxonChart data={countsByTaxonData} /> */}
    </div>
  );
};

export default Dashboard;
