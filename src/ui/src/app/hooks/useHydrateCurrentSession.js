import { useDispatch, useSelector } from "react-redux";

import { storeConfig } from "../store/config/slices/configSlice";
import { useEffect } from "react";
import { useGetRunStatusQuery } from "../store/api";
import { useRef } from "react";
import { getSessionId } from "../utils/session";

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

const useHydrateCurrentSession = () => {
  const dispatch = useDispatch();
  const configs = useSelector((state) => state?.config?.data || {});
  const rehydrated = useSelector((state) => state?._persist?.rehydrated);
  const sessionId = getSessionId();

  // If we already have configs, nothing to do.
  const haveAny = Object.keys(configs).length > 0;

  const { data: sessionMeta } = useGetRunStatusQuery(sessionId, {
    skip: !sessionId || haveAny || !rehydrated,
  });

  // Ensure we only dispatch hydration once per sessionId to avoid loops
  const didHydrateRef = useRef(false);

  useEffect(() => {
    // Wait for persist rehydration to finish to avoid overwriting persisted state.
    if (!rehydrated) return;
    if (!sessionId || haveAny) return;
    if (!sessionMeta) return;
    if (didHydrateRef.current) return;

    try {
      const effective = sessionMeta.data || sessionMeta;

      // Extract status string from nested object if needed
      // GET /status returns: data.status = { session_id, status: "...", expiryDate }
      // Extract the actual status value (could be string or nested in object)
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

      // Only include config/clusterId/clusterName if they actually exist
      // This preserves previously persisted values when /status doesn't return them
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
      didHydrateRef.current = true;
    } catch (err) {
      console.error("Failed to hydrate session config:", err);
    }
  }, [sessionMeta, sessionId, haveAny, dispatch, rehydrated]);
};

export default useHydrateCurrentSession;
