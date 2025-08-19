import axios from "axios";

const { VITE_KINFIN_API_HOST } = import.meta.env;

const getSessionId = () =>
  localStorage.getItem("currentSessionId") ||
  "6599179a64accf331ffe653db00a0e24";

const apiClient = axios.create({
  baseURL: VITE_KINFIN_API_HOST,
  headers: {
    "Content-Type": "application/json",
  },
});

export const initAnalysis = async (data) => {
  const response = await apiClient.post("/init", {
    config: data.config,
    clusterId: data.clusterId,
    isAdvanced: false,
  });
  return response.data;
};

export const getStatus = async (sessionId = getSessionId()) => {
  const response = await apiClient.get("/status", {
    headers: { "x-session-id": sessionId },
  });
  return response.data;
};

export const getBatchStatus = async (sessionIds = []) => {
  const response = await apiClient.post("/status", sessionIds, {
    headers: { "Content-Type": "application/json" },
  });
  return response.data;
};
export const getValidProteomeIds = async (data) => {
  const response = await apiClient.get("/valid-proteome-ids", {
    headers: { "x-session-id": getSessionId() },
    params: {
      page: data.page,
      size: data.size,
      clusterId: data.clusterId,
    },
  });
  return response.data;
};

export const getClusteringSets = async (data) => {
  const response = await apiClient.get("/clustering-sets", {
    params: { page: data.page, size: data.size },
  });
  return response.data;
};

export const getColumnDescriptions = async (data) => {
  const response = await apiClient.get("/column-descriptions", {
    headers: { "x-session-id": getSessionId() },
    params: { page: data.page, size: data.size, file: data.file },
  });
  return response.data;
};

export const getRunSummary = async () => {
  const response = await apiClient.get("/run-summary", {
    headers: { "x-session-id": getSessionId() },
  });
  return response.data;
};

export const getAvailableAttributes = async () => {
  const response = await apiClient.get("/available-attributes-taxonsets", {
    headers: { "x-session-id": getSessionId() },
  });
  return response.data;
};

export const getCountsByTaxon = async () => {
  const response = await apiClient.get("/counts-by-taxon", {
    headers: { "x-session-id": getSessionId() },
  });
  return response.data;
};

export const getClusterSummary = async (data) => {
  const response = await apiClient.get(`/cluster-summary/${data.attribute}`, {
    headers: { "x-session-id": getSessionId() },
    params: {
      page: data.page,
      size: data.size,
      as_file: data.asFile,
      CS_code: data.CS_code,
    },
    paramsSerializer: { indexes: null },
  });
  return response.data;
};

export const getAttributeSummary = async (data) => {
  const response = await apiClient.get(`/attribute-summary/${data.attribute}`, {
    headers: { "x-session-id": getSessionId() },
    params: {
      page: data.page,
      size: data.size,
      as_file: data.asFile,
      AS_code: data.AS_code,
    },
    paramsSerializer: { indexes: null },
  });
  return response.data;
};

export const getClusterMetrics = async (data) => {
  const response = await apiClient.get(
    `/cluster-metrics/${data.attribute}/${data.taxonSet}`,
    {
      headers: { "x-session-id": getSessionId() },
      params: {
        page: data.page,
        size: data.size,
        as_file: data.asFile,
        CM_code: data.CM_code,
      },
      paramsSerializer: { indexes: null },
    }
  );
  return response.data;
};

export const getPairwiseAnalysis = async (attribute) => {
  const response = await apiClient.get(`/pairwise-analysis/${attribute}`, {
    headers: { "x-session-id": getSessionId() },
  });
  return response.data;
};

export const getPlot = async (plotType) => {
  const response = await apiClient.get(`/plot/${plotType}`, {
    headers: { "x-session-id": getSessionId() },
    responseType: "blob",
  });
  return response.data;
};
