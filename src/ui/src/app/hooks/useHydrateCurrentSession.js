import { useDispatch, useSelector } from "react-redux";

import { getSessionId } from "../utils/session";
import { setCurrentSessionId } from "../store/config/slices/uiStateSlice";
import { storeConfig } from "../store/config/slices/configSlice";
import { useEffect } from "react";
import { useGetRunStatusQuery } from "../store/api";
import { useRef } from "react";

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

const useHydrateCurrentSession = (urlSessionId = null) => {
  const dispatch = useDispatch();
  const currentSessionId = useSelector(
    (state) => state?.config?.uiState?.currentSessionId,
  );
  const rehydrated = useSelector(
    (state) => state?._persist?.rehydrated ?? true,
  );

  // Determine the sessionId from URL first, fallback to localStorage
  const effectiveSessionId = urlSessionId || getSessionId();

  // Always call the query - don't use skip, we'll manage refetching manually
  const {
    data: sessionMeta,
    refetch,
    isFetching,
  } = useGetRunStatusQuery(effectiveSessionId);

  // Update currentSessionId when URL changes
  useEffect(() => {
    if (!effectiveSessionId || !rehydrated) return;
    if (currentSessionId === effectiveSessionId) return;

    dispatch(setCurrentSessionId(effectiveSessionId));
  }, [effectiveSessionId, currentSessionId, rehydrated, dispatch]);

  // When currentSessionId changes, refetch and hydrate
  useEffect(() => {
    if (!rehydrated) return;
    if (!currentSessionId) return;

    // Refetch to get fresh data for the new session
    refetch();
  }, [currentSessionId, rehydrated, refetch]);

  // When data arrives, determine if we should update Redux
  const didHydrateRef = useRef(false);

  useEffect(() => {
    didHydrateRef.current = false;
  }, [currentSessionId]);

  useEffect(() => {
    if (!rehydrated) return;
    if (!sessionMeta) return;
    if (!currentSessionId) return;
    if (isFetching) return; // wait for fresh data, don't process stale cache
    if (didHydrateRef.current) return;

    try {
      const effective = sessionMeta.data || sessionMeta;

      // Extract status string from nested object if needed
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

      // Map server status to UI status
      const uiStatus = mapServerStatusToUiStatus(statusValue);

      // Build payload with all available data
      const payload = {
        sessionId: currentSessionId,
        name: effective.name || `Session ${currentSessionId}`,
        meta: {
          status: uiStatus,
          isComplete: effective.isComplete ?? sessionMeta.isComplete ?? null,
          message: sessionMeta.message || null,
        },
      };

      if (effective.config) payload.config = effective.config;
      if (effective.clusterId) payload.clusterId = effective.clusterId;
      if (effective.clusterName) payload.clusterName = effective.clusterName;

      // Only dispatch if sessionId matches current (avoid stale updates)
      if (currentSessionId === (effective.sessionId || currentSessionId)) {
        dispatch(storeConfig(payload));
        didHydrateRef.current = true;
      }
    } catch (err) {
      console.error("Failed to hydrate session config:", err);
    }
  }, [sessionMeta, isFetching, currentSessionId, dispatch, rehydrated]);
};

export default useHydrateCurrentSession;
