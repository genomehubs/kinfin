import { createApi } from "@reduxjs/toolkit/query/react";

import axios from "axios";
import { storeConfig } from "./config/slices/configSlice";
import { setPollingLoading } from "./config/slices/uiStateSlice";
import { toCamelCase } from "#utils/changeCase.js";
import { getSessionId, setSessionId } from "../utils/session";

const { VITE_KINFIN_API_HOST } = import.meta.env;

// session id access is centralized in app/utils/session.js

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

/**
 * Custom base query using axios to match existing client behavior.
 * Injects session ID via x-session-id header for analysis/config endpoints.
 */
const axiosBaseQuery = async (args) => {
  const {
    url,
    method = "GET",
    data = null,
    headers = {},
    params = {},
    responseType = "json",
  } = typeof args === "string" ? { url: args } : args;

  try {
    const response = await axios({
      url: `${VITE_KINFIN_API_HOST}${url}`,
      method,
      data,
      params,
      headers: {
        "Content-Type": "application/json",
        "x-session-id": getSessionId(),
        ...headers,
      },
      responseType,
    });

    // If the response is a Blob (file/plot export), convert to a small
    // serializable object that contains an object URL and metadata so that
    // RTK Query doesn't dispatch non-serializable Blobs in action payloads.
    if (response.config && response.config.responseType === "blob") {
      const blob = response.data;
      const objectUrl = URL.createObjectURL(blob);
      return {
        data: {
          __isBlob: true,
          url: objectUrl,
          size: blob.size,
          type: blob.type,
        },
      };
    }
    // Normalize JSON response keys from snake_case to camelCase so UI
    // consistently uses camelCase `sessionId` etc.
    const normalize = (value) => {
      if (Array.isArray(value)) return value.map(normalize);
      if (value && typeof value === "object" && !(value instanceof Blob)) {
        return Object.keys(value).reduce((acc, key) => {
          const camelKey = toCamelCase(key);
          acc[camelKey] = normalize(value[key]);
          return acc;
        }, {});
      }
      return value;
    };

    return { data: normalize(response.data) };
  } catch (error) {
    return {
      error: {
        status: error.response?.status,
        data: error.response?.data || error.message,
      },
    };
  }
};

/**
 * RTK Query API slice for kinfin.
 * Replaces all redux-saga async operations.
 */
export const api = createApi({
  reducerPath: "api",
  baseQuery: axiosBaseQuery,
  tagTypes: ["config", "analysis", "status"],

  endpoints: (builder) => ({
    // ============ CONFIG ENDPOINTS ============

    /**
     * Initialize a new analysis session.
     * POST /init
     * Stores config to localStorage/IndexedDB via onQueryStarted.
     */
    initAnalysis: builder.mutation({
      query: ({ config, clusterId, isAdvanced = false, name } = {}) => ({
        url: "/init",
        method: "POST",
        data: { config, clusterId, isAdvanced, name },
      }),
      async onQueryStarted(arg, { queryFulfilled, dispatch }) {
        try {
          const { data } = await queryFulfilled;
          if (data?.sessionId) {
            setSessionId(data.sessionId);
            // prefer the name provided by the UI; fall back to server name or a default
            const storedName =
              arg?.name ?? data?.name ?? `Session ${data.sessionId}`;

            dispatch(
              storeConfig({
                sessionId: data.sessionId,
                name: storedName,
                config: arg.config,
                clusterId: arg.clusterId,
                clusterName: data.clusterName || null,
              }),
            );
            // Set loading state to show initialization is in progress
            dispatch(
              setPollingLoading({
                sessionId: data.sessionId,
                loading: true,
              }),
            );
          }
        } catch (err) {
          // Error handled by component
          console.error("initAnalysis failed:", err);
        }
      },
      invalidatesTags: ["config", "analysis"],
    }),

    /**
     * Fetch status for a single session.
     * GET /status
     * Used for polling analysis completion.
     */
    getRunStatus: builder.query({
      query: (sessionId = getSessionId()) => ({
        url: "/status",
        method: "GET",
        headers: { "x-session-id": sessionId },
      }),
      providesTags: ["status"],
    }),

    /**
     * Fetch status for multiple sessions.
     * POST /status
     * For batch status checks.
     * Stores session metadata in Redux for sidebar display.
     */
    getBatchStatus: builder.mutation({
      query: (sessionIds = []) => ({
        url: "/status",
        method: "POST",
        data: sessionIds,
      }),
      async onQueryStarted(arg, { queryFulfilled, dispatch }) {
        try {
          const { data } = await queryFulfilled;
          // Response shape: { status: "success", data: { sessions: [...] } }
          const sessions = data?.data?.sessions || data?.sessions || [];

          for (const sessionStatus of sessions) {
            // sessionStatus = { session_id: "...", status: "running", expiryDate: "..." }
            // Normalize snake_case to camelCase
            const sessionId =
              sessionStatus.session_id || sessionStatus.sessionId;
            const serverStatus = sessionStatus.status;
            const expiryDate =
              sessionStatus.expiryDate || sessionStatus.expiry_date;

            // Map server status to UI status
            const uiStatus = mapServerStatusToUiStatus(serverStatus);

            if (sessionId) {
              dispatch(
                storeConfig({
                  sessionId,
                  meta: {
                    status: uiStatus,
                    expiryDate: expiryDate,
                  },
                }),
              );
            }
          }
        } catch (err) {
          console.error("getBatchStatus error:", err);
        }
      },
      invalidatesTags: ["status"],
    }),

    /**
     * Fetch valid proteome IDs (paginated).
     * GET /valid-proteome-ids
     * Supports polling during initialization.
     */
    getValidProteomeIds: builder.query({
      // Note: server expects 1-based paging, default to page=1
      query: ({ page = 1, size = 50, clusterId } = {}) => ({
        url: "/valid-proteome-ids",
        method: "GET",
        params: { page, size, clusterId },
      }),
      providesTags: ["config"],
    }),

    /**
     * Fetch available clustering sets (paginated).
     * GET /clustering-sets
     */
    getClusteringSets: builder.query({
      query: ({ page = 1, size = 50 } = {}) => ({
        url: "/clustering-sets",
        method: "GET",
        params: { page, size },
      }),
      providesTags: ["config"],
    }),

    /**
     * Fetch column descriptions (paginated).
     * GET /column-descriptions
     */
    getColumnDescriptions: builder.query({
      query: ({ page = 1, size = 50, file } = {}) => ({
        url: "/column-descriptions",
        method: "GET",
        params: { page, size, file },
      }),
      providesTags: ["config"],
    }),

    // ============ ANALYSIS ENDPOINTS ============

    /**
     * Fetch run summary for current session.
     * GET /run-summary
     */
    getRunSummary: builder.query({
      query: () => ({
        url: "/run-summary",
        method: "GET",
      }),
      providesTags: ["analysis"],
    }),

    /**
     * Fetch available attributes and taxonsets.
     * GET /available-attributes-taxonsets
     */
    getAvailableAttributesTaxonsets: builder.query({
      query: (sessionId = getSessionId()) => ({
        url: "/available-attributes-taxonsets",
        method: "GET",
        headers: { "x-session-id": sessionId },
      }),
      providesTags: ["analysis"],
    }),

    /**
     * Fetch counts by taxon.
     * GET /counts-by-taxon
     */
    getCountsByTaxon: builder.query({
      query: (sessionId = getSessionId()) => ({
        url: "/counts-by-taxon",
        method: "GET",
        headers: { "x-session-id": sessionId },
      }),
      providesTags: ["analysis"],
    }),

    /**
     * Fetch cluster summary (paginated, supports file export).
     * GET /cluster-summary/{attribute}
     */
    getClusterSummary: builder.query({
      query: ({
        attribute,
        page = 1,
        size = 20,
        asFile = false,
        CS_code,
      } = {}) => ({
        url: `/cluster-summary/${attribute}`,
        method: "GET",
        params: {
          page,
          size,
          as_file: asFile,
          CS_code,
        },
        responseType: asFile ? "blob" : "json",
      }),
      providesTags: ["analysis"],
    }),

    /**
     * Fetch attribute summary (paginated, supports file export).
     * GET /attribute-summary/{attribute}
     */
    getAttributeSummary: builder.query({
      query: ({
        attribute,
        page = 1,
        size = 20,
        asFile = false,
        AS_code,
      } = {}) => ({
        url: `/attribute-summary/${attribute}`,
        method: "GET",
        params: {
          page,
          size,
          as_file: asFile,
          AS_code,
        },
        responseType: asFile ? "blob" : "json",
      }),
      providesTags: ["analysis"],
    }),

    /**
     * Fetch cluster metrics (paginated, supports file export).
     * GET /cluster-metrics/{attribute}/{taxonSet}
     */
    getClusterMetrics: builder.query({
      query: ({
        attribute,
        taxonSet,
        page = 1,
        size = 20,
        asFile = false,
        CM_code,
      } = {}) => ({
        url: `/cluster-metrics/${attribute}/${taxonSet}`,
        method: "GET",
        params: {
          page,
          size,
          as_file: asFile,
          CM_code,
        },
        responseType: asFile ? "blob" : "json",
      }),
      providesTags: ["analysis"],
    }),

    /**
     * Fetch pairwise analysis data.
     * GET /pairwise-analysis/{attribute}
     */
    getPairwiseAnalysis: builder.query({
      query: ({ attribute } = {}) => ({
        url: `/pairwise-analysis/${attribute}`,
        method: "GET",
      }),
      providesTags: ["analysis"],
    }),

    /**
     * Fetch plot as blob (for download/display).
     * GET /plot/{attribute}/{plotType}
     * Returns a blob (image or data file).
     */
    getPlot: builder.query({
      query: ({ attribute, plotType } = {}) => ({
        url: `/plot/${attribute}/${plotType}`,
        method: "GET",
        responseType: "blob",
      }),
      providesTags: ["analysis"],
    }),
  }),
});

export const {
  // Config hooks
  useInitAnalysisMutation,
  useGetRunStatusQuery,
  useGetBatchStatusMutation,
  useGetValidProteomeIdsQuery,
  useGetClusteringSetsQuery,
  useGetColumnDescriptionsQuery,

  // Analysis hooks
  useGetRunSummaryQuery,
  useGetAvailableAttributesTaxonsetsQuery,
  useGetCountsByTaxonQuery,
  useGetClusterSummaryQuery,
  useGetAttributeSummaryQuery,
  useGetClusterMetricsQuery,
  useGetPairwiseAnalysisQuery,
  useGetPlotQuery,
} = api;
