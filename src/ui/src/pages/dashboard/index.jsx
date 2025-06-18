import React, { useState, useEffect } from "react";
import styles from "./Dashboard.module.scss";
import {
  getAvailableAttributesTaxonsets,
  getRunSummary,
  getCountsByTaxon,
  getClusterSummary,
  getAttributeSummary,
  getClusterMetrics,
} from "../../app/store/analysis/actions";
import { getRunStatus } from "../../app/store/config/actions";
import AppLayout from "../../components/AppLayout";

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
import { useNavigate, useParams } from "react-router-dom";
import { initAnalysis } from "../../app/store/config/actions";

const Dashboard = () => {
  const navigate = useNavigate();
  const [enlargedChart, setEnlargedChart] = useState(null);
  const dispatch = useDispatch();
  const { sessionId } = useParams();
  const selectSessionDetailsById = (session_id) => (state) =>
    state?.config?.storeConfig?.data?.[session_id];
  const sessionDetails = useSelector(selectSessionDetailsById(sessionId)); // This returns the actual data
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem("currentSessionId", sessionId);
    }
  }, [sessionId]);
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.selectedAttributeTaxonset
  );

  useEffect(() => {
    dispatch(getRunStatus());
    dispatch(getAvailableAttributesTaxonsets());
    dispatch(getRunSummary());
    dispatch(getCountsByTaxon());
    dispatch(
      getClusterSummary({
        attribute: selectedAttributeTaxonset?.attribute,
      })
    );
    dispatch(
      getAttributeSummary({
        attribute: selectedAttributeTaxonset?.attribute,
      })
    );
    dispatch(
      getClusterMetrics({
        attribute: selectedAttributeTaxonset?.attribute,
        taxonSet: selectedAttributeTaxonset?.taxonset,
      })
    );
  }, [dispatch, selectedAttributeTaxonset, sessionId, sessionDetails]);

  const handleEnlarge = (chartName) => setEnlargedChart(chartName);

  const closeModal = () => setEnlargedChart(null);

  const reinitializeSession = () => {
    console.log(
      "🚀 ~ reinitializeSession ~ payload.sessionDetails:",
      sessionDetails
    );
    const payload = {
      name: sessionDetails.name,
      config: sessionDetails.config,
      navigate,
    };
    dispatch(initAnalysis(payload));
  };

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
      <AppLayout>
        {sessionDetails?.status ? (
          <>
            {" "}
            <Modal
              isOpen={!!enlargedChart}
              onClose={closeModal}
              title={modalTitleMap[enlargedChart] || ""}
            >
              {renderModalContent()}
            </Modal>
            <div className={styles.pageHeader}>
              {/* <h1 className={styles.pageTitle}>KinFin Analysis</h1> */}
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
        ) : (
          <>
            <div className={styles.page}>
              <p>
                Session is expired, Please reinitialize the session to view
                results.
              </p>
              <button
                className={styles.reinitializeButton}
                onClick={reinitializeSession}
              >
                Re-Initialize Session
              </button>
            </div>
          </>
        )}
      </AppLayout>
    </>
  );
};

export default Dashboard;
