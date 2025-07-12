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
import DataTable from "../../components/FileUpload/DataTable";

import { RunSummary } from "../../components";
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
import Modal from "@mui/material/Modal";
import Box from "@mui/material/Box";

const Dashboard = () => {
  const navigate = useNavigate();
  const [enlargedChart, setEnlargedChart] = useState(null);
  const [showDataModal, setShowDataModal] = useState(false);
  const [parsedData, setParsedData] = useState([]);
  const [validationErrors, setValidationErrors] = useState({
    headers: [],
    rows: {},
  });

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
  }, [dispatch, selectedAttributeTaxonset, sessionId, sessionDetails]);

  const handleEnlarge = (chartName) => setEnlargedChart(chartName);

  const closeModal = () => setEnlargedChart(null);

  const reinitializeSession = () => {
    const payload = {
      name: sessionDetails.name,
      config: sessionDetails.config,
      navigate,
    };
    dispatch(initAnalysis(payload));
  };
  const handleSessionClick = (session) => {
    if (!sessionDetails?.config) return;
    try {
      setParsedData(sessionDetails?.config);

      setValidationErrors({ headers: [], rows: {} });

      setShowDataModal(true);
    } catch (error) {
      console.error("Failed to parse session data:", error);
    }
  };

  const modalTitleMap = {
    attributeSummary: "Attribute Summary",
    clusterSummary: "Cluster Summary",
    clusterMetrics: "Cluster Metrics",
    // clusterAndProteinDistribution: "Cluster Distribution Per Taxon",
    // clusterAbsence: "Cluster Absence Across Taxon Sets",
    // taxonCount: "Taxon Count per Taxon Set",
  };

  const renderModalContent = () => {
    switch (enlargedChart) {
      case "attributeSummary":
        return <AttributeSummary />;
      case "clusterSummary":
        return <ClusterSummary />;
      case "clusterMetrics":
        return <ClusterMetrics />;

      default:
        return null;
    }
  };
  const handleHeaderEdit = (oldHeader, newHeader) => {
    const updatedData = parsedData.map((row) => {
      const updatedRow = { ...row };
      updatedRow[newHeader] = updatedRow[oldHeader];
      delete updatedRow[oldHeader];
      return updatedRow;
    });
    setParsedData(updatedData);
  };

  const handleCellEdit = (e, rowIdx, header) => {
    const updatedData = [...parsedData];
    updatedData[rowIdx][header] = e.target.textContent.trim();
    setParsedData(updatedData);
  };

  const renderDashboardChart = (chartKey) => {
    switch (chartKey) {
      case "attributeSummary":
        return <AttributeSummary />;
      case "clusterSummary":
        return <ClusterSummary />;
      case "clusterMetrics":
        return <ClusterMetrics />;

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
              open={!!enlargedChart}
              onClose={closeModal}
              aria-labelledby="modal-title"
              aria-describedby="modal-description"
            >
              <Box
                sx={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%, -50%)",
                  width: "90%",
                  maxWidth: 1000,
                  maxHeight: "90vh",
                  bgcolor: "var(--bg-color)",
                  color: "var(--text-color)",
                  boxShadow: 24,
                  p: 4,
                  overflowY: "auto",
                  borderRadius: 2,
                }}
              >
                <h2 id="modal-title">{modalTitleMap[enlargedChart] || ""}</h2>
                <div id="modal-description">{renderModalContent()}</div>
              </Box>
            </Modal>
            <div className={styles.pageHeader}>
              <AttributeSelector />
            </div>
            <div className={styles.page}>
              <RunSummary />
              <div className={styles.chartsContainer}>
                {Object.entries(modalTitleMap).map(([key, label]) => (
                  <div key={key} className={styles.container}>
                    <div className={styles.header}>
                      {/* <button
                        className={styles.enlargeButton}
                        onClick={() => handleEnlarge(key)}
                      >
                        <IoOpenOutline />
                      </button> */}
                      <p className={styles.title}>{label}</p>
                    </div>
                    {/* <div className={styles.chartContainer}> */}
                    {renderDashboardChart(key)}
                    {/* </div> */}
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <>
            <div className={styles.page}>
              <p>
                Session is expired for{" "}
                <span
                  style={{
                    color: "#2980b9",
                    textDecoration: "underline",
                    cursor: "pointer",
                  }}
                  onClick={() => handleSessionClick(sessionDetails)}
                >
                  {sessionDetails?.name}
                </span>
                , Please reinitialize the session to view results.
              </p>
              <button
                className={styles.reinitializeButton}
                onClick={reinitializeSession}
              >
                Re-Initialize Session
              </button>
            </div>
            <Modal
              open={showDataModal}
              onClose={() => setShowDataModal(false)}
              aria-labelledby="parsed-data-title"
            >
              <Box
                sx={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%, -50%)",
                  width: "90%",
                  maxWidth: 1000,
                  maxHeight: "90vh",
                  bgcolor: "var(--bg-color)",
                  color: "var(--text-color)",
                  boxShadow: 24,
                  p: 4,
                  overflowY: "auto",
                  borderRadius: 2,
                }}
              >
                <h2 id="parsed-data-title">{sessionDetails?.name}</h2>
                <DataTable parsedData={parsedData} allowEdit={false} />
              </Box>
            </Modal>
          </>
        )}
      </AppLayout>
    </>
  );
};

export default Dashboard;
