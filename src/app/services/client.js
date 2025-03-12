import axios from "axios";

const KINFIN_PORT = 8000;
const KINFIN_HOST = `http://127.0.0.1:${KINFIN_PORT}/kinfin`;

const getSessionId = () =>
  localStorage.getItem("session_id") || "6599179a64accf331ffe653db00a0e24";

const apiClient = axios.create({
  baseURL: KINFIN_HOST,
  headers: {
    "Content-Type": "application/json",
  },
});

export const initAnalysis = async (config) => {
  try {
    const response = await apiClient.post("/init", { config });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getStatus = async () => {
  try {
    const response = await apiClient.get("/status", {
      headers: { "x-session-id": getSessionId() },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getRunSummary = async () => {
  try {
    const response = await apiClient.get("/run-summary", {
      headers: { "x-session-id": getSessionId() },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getAvailableAttributes = async () => {
  try {
    const response = await apiClient.get("/available-attributes-taxonsets", {
      headers: { "x-session-id": getSessionId() },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getCountsByTaxon = async () => {
  try {
    const response = await apiClient.get("/counts-by-taxon", {
      headers: { "x-session-id": getSessionId() },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getClusterSummary = async (data) => {
  try {
    const response = await apiClient.get(`/cluster-summary/${data.attribute}`, {
      headers: { "x-session-id": getSessionId() },
      params: { page: data.page, size: data.size },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getAttributeSummary = async (data) => {
  try {
    const response = await apiClient.get(
      `/attribute-summary/${data.attribute}`,
      {
        headers: { "x-session-id": getSessionId() },
        params: { page: data.page, size: data.size }, // Pass pagination parameters
      }
    );
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getClusterMetrics = async (data) => {
  try {
    const response = await apiClient.get(
      `/cluster-metrics/${data.attribute}/${data.taxonSet}`,
      {
        headers: { "x-session-id": getSessionId() },
        params: { page: data.page, size: data.size },
      }
    );
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getPairwiseAnalysis = async (attribute) => {
  try {
    const response = await apiClient.get(`/pairwise-analysis/${attribute}`, {
      headers: { "x-session-id": getSessionId() },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getPlot = async (plotType) => {
  try {
    const response = await apiClient.get(`/plot/${plotType}`, {
      headers: { "x-session-id": getSessionId() },
      responseType: "blob",
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};
