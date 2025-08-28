import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";

import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import Box from "@mui/material/Box";
import ChartCard from "../../components/ChartCard";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import ClusterSizeDistribution from "../../components/Charts/ClusterSizeDistribution";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import DataTable from "../../components/FileUpload/DataTable";
import Modal from "@mui/material/Modal";
import RarefactionCurve from "../../components/Charts/RarefactionCurve";
import { RunSummary } from "../../components";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { downloadBlobFile } from "../../utils/downloadBlobFile";
import { getAttributeSummary } from "../../app/store/analysis/slices/attributeSummarySlice";
import { getAvailableAttributesTaxonsets } from "../../app/store/analysis/slices/availableAttributesTaxonsetsSlice";
import { getClusterMetrics } from "../../app/store/analysis/slices/clusterMetricsSlice";
import { getClusterSummary } from "../../app/store/analysis/slices/clusterSummarySlice";
import { getCountsByTaxon } from "../../app/store/analysis/slices/countsByTaxonSlice";
import { getRunStatus } from "../../app/store/config/slices/runStatusSlice";
import { getRunSummary } from "../../app/store/analysis/slices/runSummarySlice";
import { initAnalysis } from "../../app/store/config/slices/analysisSlice";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import styles from "./Dashboard.module.scss";

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
    (state) => state?.config?.uiState?.selectedAttributeTaxonset
  );

  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading
  );

  const rarefactionCurveBlob = useSelector(
    (state) => state?.analysis?.plot?.data?.rarefactionCurve
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
    if (!sessionDetails?.config) {
      return;
    }
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
    rarefactionCurve: "Rarefaction Curve",
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
      case "rarefactionCurve":
        if (rarefactionCurveBlob instanceof Blob) {
          downloadBlobFile(
            rarefactionCurveBlob,
            "rarefaction_curve.png",
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
      case "rarefactionCurve":
        return <RarefactionCurve />;
      case "clusterSizeDistribution":
        return <ClusterSizeDistribution />;
      default:
        return null;
    }
  };

  return (
    <AppLayout>
      {sessionDetails?.status === "active" ? (
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
                {["rarefactionCurve", "clusterSizeDistribution"].map((key) => {
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
                })}
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
