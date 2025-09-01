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
import { getAvailableAttributesTaxonsets } from "../../app/store/analysis/slices/availableAttributesTaxonsetsSlice";
import { getColumnDescriptions } from "../../app/store/config/slices/columnDescriptionsSlice";
import { getCountsByTaxon } from "../../app/store/analysis/slices/countsByTaxonSlice";
import { getRunStatus } from "../../app/store/config/slices/runStatusSlice";
import { getRunSummary } from "../../app/store/analysis/slices/runSummarySlice";
import { handleDownload } from "../../utils/downloadHandlers";
import { initAnalysis } from "../../app/store/config/slices/analysisSlice";
import { mapChartName } from "../../utils/mappings";
import styles from "./Dashboard.module.scss";
import { useSearchParams } from "react-router-dom";

const Dashboard = () => {
  const navigate = useNavigate();
  const [enlargedChart, setEnlargedChart] = useState(null);
  const [showDataModal, setShowDataModal] = useState(false);
  const [parsedData, setParsedData] = useState([]);
  const [searchParams] = useSearchParams();

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
  useEffect(() => {
    dispatch(getColumnDescriptions());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    if (!sessionId) {
      return;
    }
    const basePaths = {
      attributeSummary: "attribute-summary",
      clusterSummary: "cluster-summary",
      clusterMetrics: "cluster-metrics",
      rarefactionCurve: "rarefaction-curve",
      clusterSizeDistribution: "cluster-size-distribution",
    };
    const path = basePaths[chartKey];
    if (path) {
      navigate(`/${sessionId}/${path}?${searchParams.toString()}`);
    } else {
      console.warn("Unknown chart key:", chartKey);
    }
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
              <h2>{mapChartName(enlargedChart)}</h2>
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
                      key={key}
                      title={mapChartName(key)}
                      isDownloading={downloadLoading?.[key]}
                      onDownload={() =>
                        handleDownload({
                          chartKey: key,
                          dispatch,
                          selectedAttributeTaxonset,
                        })
                      }
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
                      key={key}
                      title={mapChartName(key)}
                      isDownloading={downloadLoading?.[key]}
                      onDownload={() =>
                        handleDownload({
                          chartKey: key,
                          dispatch,
                          selectedAttributeTaxonset,
                          rarefactionCurveBlob,
                          clusterSizeDistributionBlob,
                        })
                      }
                      onOpen={() => handleNavigate(key)}
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
