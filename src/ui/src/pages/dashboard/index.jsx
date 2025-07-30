import React, { useState, useEffect } from "react";
import styles from "./Dashboard.module.scss";
import {
  getAvailableAttributesTaxonsets,
  getRunSummary,
  getClusterSummary,
  getCountsByTaxon,
  getClusterMetrics,
  getAttributeSummary,
} from "../../app/store/analysis/actions";

import { getRunStatus } from "../../app/store/config/actions";
import AppLayout from "../../components/AppLayout";
import DataTable from "../../components/FileUpload/DataTable";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";

import { RunSummary } from "../../components";
import AttributeSelector from "../../components/AttributeSelector";
import { useDispatch, useSelector } from "react-redux";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import AllRarefactionCurve from "../../components/Charts/AllRarefactionCurve";
import ClusterSizeDistribution from "../../components/Charts/ClusterSizeDistribution";
import { useNavigate, useParams } from "react-router-dom";
import { initAnalysis } from "../../app/store/config/actions";
import { downloadBlobFile } from "../../utilis/downloadBlobFile";
import { dispatchSuccessToast } from "../../utilis/tostNotifications";
import Modal from "@mui/material/Modal";
import Box from "@mui/material/Box";

const Dashboard = () => {
  const navigate = useNavigate();
  const [enlargedChart, setEnlargedChart] = useState(null);
  const [showDataModal, setShowDataModal] = useState(false);
  const [parsedData, setParsedData] = useState([]);
  const [downloadLoading, setDownloadLoading] = useState({});

  const dispatch = useDispatch();
  const { sessionId } = useParams();
  const selectSessionDetailsById = (session_id) => (state) =>
    state?.config?.storeConfig?.data?.[session_id];
  const sessionDetails = useSelector(selectSessionDetailsById(sessionId)); // This returns the actual data
  const allRarefactionCurveBlob = useSelector(
    (state) => state?.analysis?.plot?.data?.allRarefactionCurve
  );
  const clusterSizeDistributionBlob = useSelector(
    (state) => state?.analysis?.plot?.data?.clusterSizeDistribution
  );
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

  const closeModal = () => setEnlargedChart(null);

  const reinitializeSession = () => {
    const payload = {
      name: sessionDetails.name,
      config: sessionDetails.config,
      navigate,
    };
    dispatch(initAnalysis(payload));
  };
  const handleSessionClick = () => {
    if (!sessionDetails?.config) return;
    try {
      setParsedData(sessionDetails?.config);

      setShowDataModal(true);
    } catch (error) {
      console.error("Failed to parse session data:", error);
    }
  };

  const modalTitleMap = {
    attributeSummary: "Attribute Summary",
    clusterSummary: "Cluster Summary",
    clusterMetrics: "Cluster Metrics",
    allRarefactionCurve: "All Rarefaction Curve",
    clusterSizeDistribution: "Cluster Size Distribution",
  };

  const handleDownload = (chartKey) => {
    setDownloadLoading((prev) => ({ ...prev, [chartKey]: true }));
    const attribute = selectedAttributeTaxonset?.attribute;
    const taxonSet = selectedAttributeTaxonset?.taxonset;
    const basePayload = {
      attribute,
      taxonSet,
      asFile: true,
      setDownloadLoading,
    };
    dispatchSuccessToast(`${chartKey} download has started`);

    switch (chartKey) {
      case "attributeSummary":
        dispatch(getAttributeSummary(basePayload));
        break;
      case "clusterSummary":
        dispatch(getClusterSummary(basePayload));
        break;
      case "clusterMetrics":
        dispatch(getClusterMetrics(basePayload));
        break;
      case "allRarefactionCurve": {
        if (allRarefactionCurveBlob instanceof Blob) {
          downloadBlobFile(
            allRarefactionCurveBlob,
            "all_rarefaction_curve.png",
            "image/png"
          );
        }
        setDownloadLoading((prev) => ({ ...prev, [chartKey]: false }));
        break;
      }
      case "clusterSizeDistribution": {
        if (clusterSizeDistributionBlob instanceof Blob) {
          downloadBlobFile(
            clusterSizeDistributionBlob,
            "cluster_size_distribution.png",
            "image/png"
          );
        }
        setDownloadLoading((prev) => ({ ...prev, [chartKey]: false }));
        break;
      }
      default:
        console.warn("Invalid chart key for download:", chartKey);
    }
    setTimeout(() => {
      setDownloadLoading((prev) => ({ ...prev, [chartKey]: false }));
    }, 30000);
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

  const renderDashboardChart = (chartKey) => {
    switch (chartKey) {
      case "attributeSummary":
        return <AttributeSummary />;
      case "clusterSummary":
        return <ClusterSummary />;
      case "clusterMetrics":
        return <ClusterMetrics />;
      case "allRarefactionCurve":
        return <AllRarefactionCurve />;
      case "clusterSizeDistribution":
        return <ClusterSizeDistribution />;

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
                {["attributeSummary", "clusterSummary", "clusterMetrics"].map(
                  (key) => (
                    <div key={key} className={styles.container}>
                      <div className={styles.header}>
                        <button
                          className={styles.enlargeButton}
                          onClick={() => handleDownload(key)}
                          disabled={downloadLoading[key]}
                        >
                          {downloadLoading[key] ? (
                            <div className={styles.downloadLoader} />
                          ) : (
                            <FileDownloadOutlinedIcon size="small" />
                          )}
                        </button>
                        <p className={styles.title}>{modalTitleMap[key]}</p>
                      </div>
                      {renderDashboardChart(key)}
                    </div>
                  )
                )}

                <div className={styles.rowContainer}>
                  {["allRarefactionCurve", "clusterSizeDistribution"].map(
                    (key) => (
                      <div key={key} className={styles.container}>
                        <div className={styles.header}>
                          <button
                            className={styles.enlargeButton}
                            onClick={() => handleDownload(key)}
                            disabled={downloadLoading[key]}
                          >
                            {downloadLoading[key] ? (
                              <div className={styles.downloadLoader} />
                            ) : (
                              <FileDownloadOutlinedIcon size="small" />
                            )}
                          </button>
                          <p className={styles.title}>{modalTitleMap[key]}</p>
                        </div>
                        {renderDashboardChart(key)}
                      </div>
                    )
                  )}
                </div>
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
