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
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { getRunStatus, initAnalysis } from "../../app/store/config/actions";
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
import { downloadBlobFile } from "../../utilis/downloadBlobFile";
import { dispatchSuccessToast } from "../../utilis/tostNotifications";
import Modal from "@mui/material/Modal";
import Box from "@mui/material/Box";
import ChartCard from "../../components/ChartCard";
import { setDownloadLoading } from "../../app/store/config/actions";

const Dashboard = () => {
  const navigate = useNavigate();
  const [enlargedChart, setEnlargedChart] = useState(null);
  const [showDataModal, setShowDataModal] = useState(false);
  const [parsedData, setParsedData] = useState([]);

  const dispatch = useDispatch();
  const { sessionId } = useParams();

  const sessionDetails = useSelector(
    (state) => state?.config?.storeConfig?.data?.[sessionId]
  );

  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.selectedAttributeTaxonset
  );

  const downloadLoading = useSelector(
    (state) => state?.config?.downloadLoading
  );

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
      clusterId: sessionDetails.clusterId,
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

  const handleNavigate = (chartKey) => {
    if (!sessionId) return;
    const basePaths = {
      attributeSummary: "attribute-summary",
      clusterSummary: "cluster-summary",
      clusterMetrics: "cluster-metrics",
    };
    const path = basePaths[chartKey];
    if (path) navigate(`/${sessionId}/${path}`);
    else console.warn("Unknown chart key:", chartKey);
  };

  const modalTitleMap = {
    attributeSummary: "Attribute Summary",
    clusterSummary: "Cluster Summary",
    clusterMetrics: "Cluster Metrics",
    allRarefactionCurve: "All Rarefaction Curve",
    clusterSizeDistribution: "Cluster Size Distribution",
  };

  const handleDownload = (chartKey) => {
    dispatch(setDownloadLoading({ type: chartKey, loading: true }));

    const attribute = selectedAttributeTaxonset?.attribute;
    const taxonSet = selectedAttributeTaxonset?.taxonset;
    const basePayload = {
      attribute,
      taxonSet,
      asFile: true,
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
      case "allRarefactionCurve":
        if (allRarefactionCurveBlob instanceof Blob) {
          downloadBlobFile(
            allRarefactionCurveBlob,
            "all_rarefaction_curve.png",
            "image/png"
          );
          dispatch(setDownloadLoading({ type: chartKey, loading: false }));
        }
        break;
      case "clusterSizeDistribution":
        if (clusterSizeDistributionBlob instanceof Blob) {
          downloadBlobFile(
            clusterSizeDistributionBlob,
            "cluster_size_distribution.png",
            "image/png"
          );
          dispatch(setDownloadLoading({ type: chartKey, loading: false }));
        }
        break;
      default:
        console.warn("Invalid chart key for download:", chartKey);
    }

    setTimeout(() => {
      dispatch(setDownloadLoading({ type: chartKey, loading: false }));
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
    <AppLayout>
      {sessionDetails?.status ? (
        <>
          <Modal open={!!enlargedChart} onClose={closeModal}>
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
              <h2>{modalTitleMap[enlargedChart] || ""}</h2>
              <div>{renderModalContent()}</div>
            </Box>
          </Modal>

          <div className={styles.pageHeader}>
            <AttributeSelector />
          </div>
          <div className={styles.page}>
            <RunSummary />
            <div className={styles.chartsContainer}>
              {["attributeSummary", "clusterSummary", "clusterMetrics"].map(
                (key) => {
                  return (
                    <ChartCard
                      title={modalTitleMap[key]}
                      isDownloading={downloadLoading?.[key]}
                      onDownload={() => handleDownload(key)}
                      onOpen={() => handleNavigate(key)}
                    >
                      {renderDashboardChart(key)}
                    </ChartCard>
                  );
                }
              )}

              <div className={styles.rowContainer}>
                {["allRarefactionCurve", "clusterSizeDistribution"].map(
                  (key) => {
                    return (
                      <ChartCard
                        title={modalTitleMap[key]}
                        isDownloading={downloadLoading?.[key]}
                        onDownload={() => handleDownload(key)}
                        widthPercent={48}
                      >
                        {renderDashboardChart(key)}
                      </ChartCard>
                    );
                  }
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
          <Modal open={showDataModal} onClose={() => setShowDataModal(false)}>
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
              <h2>{sessionDetails?.name}</h2>
              <DataTable parsedData={parsedData} allowEdit={false} />
            </Box>
          </Modal>
        </>
      )}
    </AppLayout>
  );
};

export default Dashboard;
