import {
  setPollingLoading,
  setSelectedAttributeTaxonset as setSelectedAttributeTaxonsetAction,
} from "../../app/store/config/slices/uiStateSlice";
import { useCallback, useEffect, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useParams, useSearchParams } from "react-router-dom";

import { serializeCodes } from "../../app/utils/columnCodes";
import { setSessionId } from "../../app/utils/session";
import useColumnDescriptions from "#hooks/useColumnDescriptions.js";
import useColumnDescriptionsSets from "#hooks/useColumnDescriptionsSets.js";
import usePlot from "#hooks/usePlot";
import useSessionPolling from "#hooks/useSessionPolling";

const CODE_PARAMS = ["AS_code", "CS_code", "CM_code"];

const useDashboardData = () => {
  const dispatch = useDispatch();
  const { sessionId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();

  // Restore all column code params at once from Redux when they're missing from URL
  const columnSettings = useSelector(
    (s) => s?.config?.uiState?.columnSettings || {},
  );
  useEffect(() => {
    const missing = CODE_PARAMS.filter(
      (k) => !searchParams.has(k) && columnSettings[k]?.length > 0,
    );
    if (missing.length === 0) return;
    setSearchParams(
      (prev) => {
        const newParams = new URLSearchParams(prev);
        missing.forEach((k) => {
          if (!newParams.has(k)) {
            const serialized = serializeCodes(columnSettings[k]);
            if (serialized) newParams.append(k, serialized);
          }
        });
        return newParams;
      },
      { replace: true },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [columnSettings]);

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
    { attribute, plotType: "rarefaction-curve", sessionId },
    { skip: !attribute, refetchOnMountOrArgChange: true },
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
    { attribute, plotType: "cluster-size-distribution", sessionId },
    { skip: !attribute, refetchOnMountOrArgChange: true },
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
