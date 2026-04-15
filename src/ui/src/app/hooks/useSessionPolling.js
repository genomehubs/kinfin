import { useEffect, useState } from "react";

import { setPollingLoading } from "../store/config/slices/uiStateSlice";
import { storeConfig } from "../store/config/slices/configSlice";
import { useDispatch } from "react-redux";
import { useGetRunStatusQuery } from "#store/api";

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

export default function useSessionPolling(sessionId) {
  const dispatch = useDispatch();
  const [shouldContinuePolling, setShouldContinuePolling] = useState(true);

  const {
    data: sessionMeta,
    isLoading: sessionLoading,
    isFetching,
  } = useGetRunStatusQuery(sessionId, {
    skip: !sessionId,
    pollingInterval: shouldContinuePolling && sessionId ? 2000 : 0,
  });

  useEffect(() => {
    if (!sessionId) return;
    const effective = sessionMeta?.data || sessionMeta;
    const isComplete = effective?.isComplete ?? effective?.is_complete ?? false;
    setShouldContinuePolling(!isComplete);
  }, [sessionMeta, sessionId]);

  useEffect(() => {
    if (!sessionMeta || !sessionId || isFetching) return;
    try {
      const effective = sessionMeta.data || sessionMeta;

      let statusValue = null;
      if (typeof effective.status === "string") {
        statusValue = effective.status;
      } else if (
        effective.status &&
        typeof effective.status === "object" &&
        effective.status.status
      ) {
        statusValue = effective.status.status;
      } else if (sessionMeta.status && typeof sessionMeta.status === "string") {
        statusValue = sessionMeta.status;
      }

      const uiStatus = mapServerStatusToUiStatus(statusValue);

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

      // Manage loading overlay
      const isLoadingSession = !sessionMeta || effective?.isComplete === false;
      dispatch(setPollingLoading({ sessionId, loading: isLoadingSession }));
    } catch (err) {
      console.error(
        "Failed to process session meta in useSessionPolling:",
        err,
      );
    }
  }, [sessionMeta, isFetching, sessionId, dispatch]);

  const isLoadingSession =
    !sessionMeta || sessionMeta?.data?.isComplete === false || sessionLoading;

  return {
    sessionMeta,
    sessionLoading,
    shouldContinuePolling,
    setShouldContinuePolling,
    isLoadingSession,
  };
}
