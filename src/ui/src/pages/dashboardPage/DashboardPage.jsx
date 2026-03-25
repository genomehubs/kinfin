import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";

import AppLayout from "#components/AppLayout";
import AttributeSelector from "#components/AttributeSelector";
import AttributeSummary from "#components/Charts/AttributeSummary";
import Box from "@mui/material/Box";
import ChartCard from "#components/ChartCard";
import ClusterMetrics from "#components/Charts/ClusterMetrics";
import ClusterSizeDistribution from "#components/Charts/ClusterSizeDistribution";
import ClusterSummary from "#components/Charts/ClusterSummary";
import DataTable from "#components/FileUpload/DataTable";
import Modal from "@mui/material/Modal";
import RarefactionCurve from "#components/Charts/RarefactionCurve";
import RunSummary from "#components/RunSummary";
import { handleDownload } from "../../utils/downloadHandlers";
import { mapChartName } from "../../utils/mappings";
import { storeConfig } from "../../app/store/config/slices/configSlice";
import { setPollingLoading } from "../../app/store/config/slices/uiStateSlice";
import styles from "./Dashboard.module.scss";
import useColumnDescriptions from "#hooks/useColumnDescriptions.js";
import useColumnDescriptionsSets from "#hooks/useColumnDescriptionsSets.js";
import { useGetRunStatusQuery } from "#store/api";
import { useInitAnalysis } from "#hooks/useInitAnalysis";
import usePlot from "#hooks/usePlot";
import { useSearchParams } from "react-router-dom";

/**
 * Map server status values to UI status values.
 * Server returns: "running", "pending", "completed", "error", "not_initialized"
 * UI expects: "initialising", "active", "error", "inactive"
 */
const mapServerStatusToUiStatus = (serverStatus) => {
  if (!serverStatus) return "inactive";

  switch (serverStatus) {
    case "running":
    case "pending":
      return "initialising";
    case "completed":
      return "active";
    case "error":
      return "error";
    case "not_initialized":
    case "inactive":
      return "inactive";
    default:
      return "inactive";
  }
};

const DashboardPage = () => {
  const navigate = useNavigate();
  const [enlargedChart, setEnlargedChart] = useState(null);
  const [showDataModal, setShowDataModal] = useState(false);
  const [parsedData, setParsedData] = useState([]);
  const [shouldContinuePolling, setShouldContinuePolling] = useState(true);
  const [searchParams] = useSearchParams();

  const dispatch = useDispatch();
  const { sessionId } = useParams();

  // ensure column descriptions are fetched (replaces dispatch(getColumnDescriptions()))
  const { data: _fetchedColumnDescriptions = [] } = useColumnDescriptions();
  const { attributeSummary, clusterSummary, clusterMetrics } =
    useColumnDescriptionsSets();
  const { initAnalysis: initAnalysisMutation } = useInitAnalysis();

  const sessionDetails = useSelector(
    (state) => state?.config?.data?.[sessionId],
  );
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading,
  );

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem("currentSessionId", sessionId);
    }
  }, [sessionId]);

  // Derive selected attribute/taxon from store when container HOC removed
  const selectedFromStore = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset,
  );

  const attribute = selectedFromStore?.attribute ?? "all";
  const taxonset = selectedFromStore?.taxonset ?? "all";

  const dispatchSetSelected = (payload) =>
    dispatch({ type: "uiState/setSelectedAttributeTaxonset", payload });

  const selectedAttributeTaxonsetLocal = { attribute, taxonset };

  // Fetch plot blobs individually for dashboard downloads
  const { data: rarefactionResp } = usePlot(
    { attribute, plotType: "rarefaction-curve" },
    { skip: !attribute },
  );
  const rarefactionCurveBlob = rarefactionResp?.data ?? rarefactionResp ?? null;

  const { data: csdResp } = usePlot(
    { attribute, plotType: "cluster-size-distribution" },
    { skip: !attribute },
  );
  const clusterSizeDistributionBlob = csdResp?.data ?? csdResp ?? null;

  // Load session metadata from API (source of truth) and store in redux
  // Poll every 2 seconds ONLY while analysis is initializing (isComplete is false)
  const {
    data: sessionMeta,
    isLoading: sessionLoading,
    // isFetching: sessionFetching,
    // error: sessionError,
  } = useGetRunStatusQuery(sessionId, {
    skip: !sessionId,
    pollingInterval: shouldContinuePolling && sessionId ? 2000 : 0,
  });

  // Update polling state based on whether analysis is complete
  // This breaks the circularity: pollingInterval depends on shouldContinuePolling state,
  // and shouldContinuePolling is updated in effect based on sessionMeta response
  useEffect(() => {
    if (sessionMeta) {
      const isComplete =
        sessionMeta?.data?.isComplete ?? sessionMeta?.isComplete;
      setShouldContinuePolling(!isComplete);
    }
  }, [sessionMeta]);

  useEffect(() => {
    if (sessionMeta && sessionId) {
      try {
        // Normalize: API responses may wrap payload under `data` (ResponseSchema.data)
        const effective = sessionMeta.data || sessionMeta;

        // Extract status string from nested object if needed
        // GET /status returns: data.status = { session_id, status: "...", expiryDate }
        let statusValue = null;
        if (typeof effective.status === "string") {
          statusValue = effective.status;
        } else if (
          effective.status &&
          typeof effective.status === "object" &&
          effective.status.status
        ) {
          statusValue = effective.status.status;
        } else if (
          sessionMeta.status &&
          typeof sessionMeta.status === "string"
        ) {
          statusValue = sessionMeta.status;
        }

        // Map server status to UI status
        const uiStatus = mapServerStatusToUiStatus(statusValue);

        // Only include config/clusterId/clusterName if they actually exist
        // This preserves previously stored values when /status doesn't return them
        const payload = {
          sessionId,
          name: effective.name || `Session ${sessionId}`,
          meta: {
            status: uiStatus,
            isComplete: effective.isComplete ?? sessionMeta.isComplete ?? null,
            message: sessionMeta.message || null,
          },
        };

        if (effective.config) payload.config = effective.config;
        if (effective.clusterId) payload.clusterId = effective.clusterId;
        if (effective.clusterName) payload.clusterName = effective.clusterName;

        dispatch(storeConfig(payload));
      } catch (err) {
        console.error("Failed to store session metadata:", err);
      }
    }
  }, [sessionMeta, sessionId, dispatch]);

  // Only fetch analysis data once we have session metadata/config available.
  const effectiveMeta = sessionMeta?.data ? sessionMeta.data : sessionMeta;

  // Derive server-reported status string for easier checks
  const serverStatus = effectiveMeta
    ? typeof effectiveMeta.status === "string"
      ? effectiveMeta.status
      : effectiveMeta.status?.status || null
    : null;

  // Show loading overlay only when we don't have data yet OR the server says it's not complete
  // Don't show it just because a polling request is in flight (that causes flickering)
  const isLoadingSession = !sessionMeta || effectiveMeta?.isComplete === false;

  // Manage loading overlay state based on session initialization progress
  useEffect(() => {
    if (!sessionId) return;

    dispatch(
      setPollingLoading({
        sessionId,
        loading: isLoadingSession,
      }),
    );
  }, [sessionId, isLoadingSession, dispatch]);

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

  const renderModalContent = () => {
    switch (enlargedChart) {
      case "attributeSummary":
        return (
          <AttributeSummary
            attribute={selectedAttributeTaxonsetLocal.attribute}
            attributeSummaryColumnDescriptions={attributeSummary}
          />
        );
      case "clusterSummary":
        return (
          <ClusterSummary
            attribute={selectedAttributeTaxonsetLocal.attribute}
            clusterSummaryColumnDescriptions={clusterSummary}
          />
        );
      case "clusterMetrics":
        return (
          <ClusterMetrics
            attribute={selectedAttributeTaxonsetLocal.attribute}
            taxonset={selectedAttributeTaxonsetLocal.taxonset}
            clusterMetricsColumnDescriptions={clusterMetrics}
          />
        );
      default:
        return null;
    }
  };

  const renderDashboardChart = (chartKey) => {
    switch (chartKey) {
      case "attributeSummary":
        return (
          <AttributeSummary
            attribute={selectedAttributeTaxonsetLocal.attribute}
            attributeSummaryColumnDescriptions={attributeSummary}
          />
        );
      case "clusterSummary":
        return (
          <ClusterSummary
            attribute={selectedAttributeTaxonsetLocal.attribute}
            clusterSummaryColumnDescriptions={clusterSummary}
          />
        );
      case "clusterMetrics":
        return (
          <ClusterMetrics
            attribute={selectedAttributeTaxonsetLocal.attribute}
            taxonset={selectedAttributeTaxonsetLocal.taxonset}
            clusterMetricsColumnDescriptions={clusterMetrics}
          />
        );
      case "rarefactionCurve":
        return (
          <RarefactionCurve
            attribute={selectedAttributeTaxonsetLocal.attribute}
          />
        );
      case "clusterSizeDistribution":
        return (
          <ClusterSizeDistribution
            attribute={selectedAttributeTaxonsetLocal.attribute}
            clusterSizeDistributionBlob={clusterSizeDistributionBlob}
          />
        );
      default:
        return null;
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
                          selectedAttributeTaxonset:
                            selectedAttributeTaxonsetLocal,
                        })
                      }
                      onOpen={() => handleNavigate(key)}
                    >
                      {renderDashboardChart(key)}
                    </ChartCard>
                  );
                },
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
                          selectedAttributeTaxonset:
                            selectedAttributeTaxonsetLocal,
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

export default DashboardPage;
