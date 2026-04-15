import React, { useEffect, useState } from "react";
import { mainCharts, rowCharts } from "./descriptors";

import AppLayout from "#components/AppLayout";
import AttributeSelector from "#components/AttributeSelector";
import Box from "@mui/material/Box";
import ChartCard from "#components/ChartCard";
import DashboardChartRenderer from "./DashboardChartRenderer";
import DataTable from "#components/FileUpload/DataTable";
import EnlargedChartModal from "./EnlargedChartModal";
import Modal from "@mui/material/Modal";
import RunSummary from "#components/RunSummary";
import { handleDownload } from "../../utils/downloadHandlers";
import styles from "./Dashboard.module.scss";
import useDashboardData from "./useDashboardData";
import { useInitAnalysis } from "#hooks/useInitAnalysis";
import { useNavigate } from "react-router-dom";
import { useSearchParams } from "react-router-dom";

const DashboardPage = () => {
  const navigate = useNavigate();
  const [enlargedChart, setEnlargedChart] = useState(null);
  const [showDataModal, setShowDataModal] = useState(false);
  const [parsedData, setParsedData] = useState([]);
  const [searchParams] = useSearchParams();

  const { initAnalysis: initAnalysisMutation } = useInitAnalysis();

  const {
    dispatch,
    sessionId,
    attribute,
    taxonset,
    dispatchSetSelected,
    selectedAttributeTaxonsetLocal,
    rarefactionCurveBlob,
    clusterSizeDistributionBlob,
    sessionLoading,
    isLoadingSession,
    effectiveMeta,
    serverStatus,
    sessionDetails,
    downloadLoading,
    attributeSummary,
    clusterSummary,
    clusterMetrics,
  } = useDashboardData();

  // Show loading overlay only when we don't have data yet OR the server says it's not complete
  // Don't show it just because a polling request is in flight (that causes flickering)
  // `isLoadingSession` is provided by `useSessionPolling` hook

  // Manage loading overlay state based on session initialization progress
  // `setPollingLoading` is handled inside `useDashboardData` hook now.

  useEffect(() => {
    // always attempt to refresh run status locally
    // run status is fetched via `useGetRunStatusQuery`; remove legacy dispatch

    // If session status is still loading initially, don't fetch analysis queries yet
    if (sessionLoading) return;

    // Only dispatch analysis queries when we have a sessionId and either a stored config
    // or the server indicates the run is complete (so results will be available).
    const readyForAnalysis =
      sessionId &&
      (sessionDetails?.config || effectiveMeta?.isComplete === true);
    if (!readyForAnalysis) return;

    // Analysis components fetch their data via RTK Query hooks.
  }, [dispatch, sessionId, sessionDetails, sessionLoading, effectiveMeta]);

  const closeModal = () => setEnlargedChart(null);

  const reinitializeSession = () => {
    // Call the RTK Query mutation to re-run initialization using stored config
    if (!sessionDetails?.config) return;
    (async () => {
      try {
        const result = await initAnalysisMutation({
          config: sessionDetails.config,
          clusterId: sessionDetails.clusterId,
          isAdvanced: false,
          name: sessionDetails?.name,
        }).unwrap();

        const newSessionId = result?.sessionId ?? result?.data?.sessionId;
        if (newSessionId) {
          navigate(`/${newSessionId}/`);
        }
      } catch (err) {
        console.error("Reinitialize analysis failed:", err);
      }
    })();
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

  // Determine whether to show loading, active dashboard, or reinitialize prompt.
  // If metadata is being fetched, show loading. Otherwise consider run status.
  const isSessionActive =
    // prefer the local stored status when available
    sessionDetails?.status === "active" ||
    // otherwise use the server-reported status string or completion flag
    serverStatus === "success" ||
    serverStatus === "completed" ||
    serverStatus === "active" ||
    effectiveMeta?.is_complete === true;

  // (kept for backward compatibility above)

  return (
    <AppLayout>
      {isLoadingSession ? (
        <div className={styles.page}>
          <p>Loading session data...</p>
        </div>
      ) : isSessionActive ? (
        <>
          <EnlargedChartModal
            enlargedChart={enlargedChart}
            open={!!enlargedChart}
            onClose={closeModal}
            selectedAttributeTaxonsetLocal={selectedAttributeTaxonsetLocal}
            attributeSummary={attributeSummary}
            clusterSummary={clusterSummary}
            clusterMetrics={clusterMetrics}
          />

          <div className={styles.pageHeader}>
            <AttributeSelector
              sessionId={sessionId}
              attribute={attribute}
              taxonset={taxonset}
              setSelectedAttributeTaxonset={dispatchSetSelected}
              isLoading={isLoadingSession}
            />
          </div>
          <div className={styles.page}>
            <RunSummary />
            <div className={styles.chartsContainer}>
              {/* main charts */}
              {mainCharts.map((desc) => (
                <React.Fragment key={desc.key}>
                  <ChartCard
                    title={desc.title}
                    isDownloading={downloadLoading?.[desc.chartKey]}
                    onDownload={() =>
                      handleDownload({
                        chartKey: desc.chartKey,
                        dispatch,
                        selectedAttributeTaxonset:
                          selectedAttributeTaxonsetLocal,
                      })
                    }
                    onOpen={() => handleNavigate(desc.chartKey)}
                  >
                    <DashboardChartRenderer
                      chartKey={desc.chartKey}
                      selectedAttributeTaxonsetLocal={
                        selectedAttributeTaxonsetLocal
                      }
                      attributeSummary={attributeSummary}
                      clusterSummary={clusterSummary}
                      clusterMetrics={clusterMetrics}
                      clusterSizeDistributionBlob={clusterSizeDistributionBlob}
                    />
                  </ChartCard>
                </React.Fragment>
              ))}

              <div className={styles.rowContainer}>
                {rowCharts.map((desc) => {
                  const blob =
                    desc.chartKey === "rarefactionCurve"
                      ? rarefactionCurveBlob
                      : desc.chartKey === "clusterSizeDistribution"
                        ? clusterSizeDistributionBlob
                        : null;
                  return (
                    <ChartCard
                      key={desc.key}
                      title={desc.title}
                      isDownloading={downloadLoading?.[desc.chartKey]}
                      onDownload={() =>
                        handleDownload({
                          chartKey: desc.chartKey,
                          dispatch,
                          selectedAttributeTaxonset:
                            selectedAttributeTaxonsetLocal,
                          blob,
                        })
                      }
                      onOpen={() => handleNavigate(desc.chartKey)}
                      widthPercent={desc.widthPercent}
                    >
                      <DashboardChartRenderer
                        chartKey={desc.chartKey}
                        selectedAttributeTaxonsetLocal={
                          selectedAttributeTaxonsetLocal
                        }
                        attributeSummary={attributeSummary}
                        clusterSummary={clusterSummary}
                        clusterMetrics={clusterMetrics}
                        clusterSizeDistributionBlob={
                          clusterSizeDistributionBlob
                        }
                      />
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

export default DashboardPage;
