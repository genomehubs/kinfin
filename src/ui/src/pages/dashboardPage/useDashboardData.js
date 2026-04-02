import { useEffect, useMemo, useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useParams } from "react-router-dom";
import usePlot from "#hooks/usePlot";
import useSessionPolling from "#hooks/useSessionPolling";
import useColumnDescriptions from "#hooks/useColumnDescriptions.js";
import useColumnDescriptionsSets from "#hooks/useColumnDescriptionsSets.js";
import {
  setPollingLoading,
  setSelectedAttributeTaxonset as setSelectedAttributeTaxonsetAction,
} from "../../app/store/config/slices/uiStateSlice";
import { setSessionId } from "../../app/utils/session";

const useDashboardData = () => {
  const dispatch = useDispatch();
  const { sessionId } = useParams();

  // ensure column descriptions are fetched
  const { data: _fetchedColumnDescriptions = [] } = useColumnDescriptions();
  const { attributeSummary, clusterSummary, clusterMetrics } =
    useColumnDescriptionsSets();

  useEffect(() => {
    if (sessionId) {
      setSessionId(sessionId);
    }
  }, [sessionId]);

  // derive selected attribute/taxon
  const selectedFromStore = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset,
  );
  const attribute = selectedFromStore?.attribute ?? "all";
  const taxonset = selectedFromStore?.taxonset ?? "all";
  const dispatchSetSelected = useCallback(
    (payload) => dispatch(setSelectedAttributeTaxonsetAction(payload)),
    [dispatch],
  );
  const selectedAttributeTaxonsetLocal = useMemo(
    () => ({ attribute, taxonset }),
    [attribute, taxonset],
  );

  // plot blobs for dashboard (capture loading and error)
  const {
    data: rarefactionResp,
    isLoading: isRarefactionLoading,
    error: rarefactionError,
  } = usePlot(
    { attribute, plotType: "rarefaction-curve" },
    { skip: !attribute },
  );
  const rarefactionCurve = useMemo(
    () => ({
      data: rarefactionResp?.data ?? rarefactionResp ?? null,
      isLoading: !!isRarefactionLoading,
      error: rarefactionError ?? null,
      filename: null,
    }),
    [rarefactionResp, isRarefactionLoading, rarefactionError],
  );

  const {
    data: csdResp,
    isLoading: isCsdLoading,
    error: csdError,
  } = usePlot(
    { attribute, plotType: "cluster-size-distribution" },
    { skip: !attribute },
  );
  const clusterSizeDistribution = useMemo(
    () => ({
      data: csdResp?.data ?? csdResp ?? null,
      isLoading: !!isCsdLoading,
      error: csdError ?? null,
      filename: null,
    }),
    [csdResp, isCsdLoading, csdError],
  );

  const {
    sessionMeta,
    sessionLoading,
    isLoadingSession,
    error: sessionError,
  } = useSessionPolling(sessionId);

  const effectiveMeta = useMemo(
    () => (sessionMeta?.data ? sessionMeta.data : sessionMeta),
    [sessionMeta],
  );

  const serverStatus = useMemo(() => {
    if (!effectiveMeta) return null;
    return typeof effectiveMeta.status === "string"
      ? effectiveMeta.status
      : effectiveMeta.status?.status || null;
  }, [effectiveMeta]);

  // update polling loading indicator in store
  useEffect(() => {
    if (!sessionId) return;

    try {
      dispatch(
        setPollingLoading({
          sessionId,
          loading: isLoadingSession,
        }),
      );
    } catch (err) {
      // swallow errors — tests may mock dispatch
      // eslint-disable-next-line no-console
      console.error("Failed to set polling loading in hook:", err);
    }
  }, [sessionId, isLoadingSession, dispatch]);

  const sessionDetails = useSelector(
    (state) => state?.config?.data?.[sessionId],
  );
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading,
  );

  const isPlotsLoading =
    rarefactionCurve.isLoading || clusterSizeDistribution.isLoading;

  const isSessionActive = useMemo(() => {
    return (
      sessionDetails?.status === "active" ||
      serverStatus === "success" ||
      serverStatus === "completed" ||
      serverStatus === "active" ||
      effectiveMeta?.is_complete === true
    );
  }, [sessionDetails, serverStatus, effectiveMeta]);

  const readyForAnalysis = useMemo(() => {
    return (
      !!sessionId &&
      (Boolean(sessionDetails?.config) ||
        effectiveMeta?.isComplete === true ||
        effectiveMeta?.is_complete === true)
    );
  }, [sessionId, sessionDetails, effectiveMeta]);

  return useMemo(
    () => ({
      dispatch,
      sessionId,
      attribute,
      taxonset,
      dispatchSetSelected,
      selectedAttributeTaxonsetLocal,
      rarefactionCurve,
      clusterSizeDistribution,
      sessionMeta,
      sessionLoading,
      isLoadingSession,
      effectiveMeta,
      serverStatus,
      sessionDetails,
      downloadLoading,
      attributeSummary,
      clusterSummary,
      clusterMetrics,
      isPlotsLoading,
      isSessionActive,
      readyForAnalysis,
      sessionError,
    }),
    [
      dispatch,
      sessionId,
      attribute,
      taxonset,
      dispatchSetSelected,
      selectedAttributeTaxonsetLocal,
      rarefactionCurve,
      clusterSizeDistribution,
      sessionMeta,
      sessionLoading,
      isLoadingSession,
      effectiveMeta,
      serverStatus,
      sessionDetails,
      downloadLoading,
      attributeSummary,
      clusterSummary,
      clusterMetrics,
      isPlotsLoading,
      isSessionActive,
      readyForAnalysis,
      sessionError,
    ],
  );
};

export default useDashboardData;
