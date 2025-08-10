import {
  INIT_ANALYSIS,
  INIT_ANALYSIS_SUCCESS,
  INIT_ANALYSIS_FAILURE,
  INIT_ANALYSIS_RESET,
  GET_RUN_STATUS,
  GET_RUN_STATUS_SUCCESS,
  GET_RUN_STATUS_FAILURE,
  GET_RUN_STATUS_RESET,
  SET_SELECTED_ATTRIBUTE_TAXONSET,
  STORE_CONFIG,
  STORE_CONFIG_RESET,
  RENAME_CONFIG,
  DELETE_CONFIG,
  GET_VALID_PROTEOME_IDS,
  GET_VALID_PROTEOME_IDS_SUCCESS,
  GET_VALID_PROTEOME_IDS_FAILURE,
  GET_VALID_PROTEOME_IDS_RESET,
  SET_POLLING_LOADING,
  GET_BATCH_STATUS,
  GET_BATCH_STATUS_SUCCESS,
  GET_BATCH_STATUS_FAILURE,
  GET_BATCH_STATUS_RESET,
  UPDATE_SESSION_META,
  GET_CLUSTERING_SETS,
  GET_CLUSTERING_SETS_SUCCESS,
  GET_CLUSTERING_SETS_FAILURE,
  GET_CLUSTERING_SETS_RESET,
  SET_SELECTED_CLUSTER_SET,
  SET_DOWNLOAD_LOADING,
  GET_COLUMN_DESCRIPTIONS,
  GET_COLUMN_DESCRIPTIONS_SUCCESS,
  GET_COLUMN_DESCRIPTIONS_FAILURE,
  GET_COLUMN_DESCRIPTIONS_RESET,
} from "./actionTypes";

export const initAnalysis = (data) => ({
  type: INIT_ANALYSIS,
  payload: data,
});

export const initAnalysisSuccess = (data) => ({
  type: INIT_ANALYSIS_SUCCESS,
  payload: data,
});

export const initAnalysisFailure = (data) => ({
  type: INIT_ANALYSIS_FAILURE,
  payload: data,
});

export const initAnalysisReset = () => ({
  type: INIT_ANALYSIS_RESET,
});

export const getRunStatus = (data) => ({
  type: GET_RUN_STATUS,
  payload: data,
});

export const getRunStatusSuccess = (data) => ({
  type: GET_RUN_STATUS_SUCCESS,
  payload: data,
});

export const getRunStatusFailure = (data) => ({
  type: GET_RUN_STATUS_FAILURE,
  payload: data,
});

export const getRunStatusReset = () => ({
  type: GET_RUN_STATUS_RESET,
});

export const setSelectedAttributeTaxonset = (data) => ({
  type: SET_SELECTED_ATTRIBUTE_TAXONSET,
  payload: data,
});

export const storeConfig = (data) => ({
  type: STORE_CONFIG,
  payload: data,
});

export const storeConfigReset = () => ({
  type: STORE_CONFIG_RESET,
});

export const renameConfig = (data) => ({
  type: RENAME_CONFIG,
  payload: data,
});
export const deleteConfig = (data) => ({
  type: DELETE_CONFIG,
  payload: data,
});

export const getValidProteomeIds = (data) => {
  return {
    type: GET_VALID_PROTEOME_IDS,
    payload: data,
  };
};

export const getValidProteomeIdsSuccess = (data) => ({
  type: GET_VALID_PROTEOME_IDS_SUCCESS,
  payload: data,
});

export const getValidProteomeIdsFailure = (data) => ({
  type: GET_VALID_PROTEOME_IDS_FAILURE,
  payload: data,
});

export const getValidProteomeIdsReset = () => ({
  type: GET_VALID_PROTEOME_IDS_RESET,
});

export const setPollingLoading = (data) => ({
  type: SET_POLLING_LOADING,
  payload: data,
});

export const setDownloadLoading = (data) => ({
  type: SET_DOWNLOAD_LOADING,
  payload: data,
});

export const getBatchStatus = (data) => ({
  type: GET_BATCH_STATUS,
  payload: data,
});

export const getBatchStatusSuccess = (data) => ({
  type: GET_BATCH_STATUS_SUCCESS,
  payload: data,
});

export const getBatchStatusFailure = (data) => ({
  type: GET_BATCH_STATUS_FAILURE,
  payload: data,
});

export const getBatchStatusReset = () => ({
  type: GET_BATCH_STATUS_RESET,
});

export const updateSessionMeta = (sessionId, meta) => ({
  type: UPDATE_SESSION_META,
  payload: { sessionId, meta },
});

export const getClusteringSets = (data) => ({
  type: GET_CLUSTERING_SETS,
  payload: data,
});

export const getClusteringSetsSuccess = (data) => ({
  type: GET_CLUSTERING_SETS_SUCCESS,
  payload: data,
});

export const getClusteringSetsFailure = (data) => ({
  type: GET_CLUSTERING_SETS_FAILURE,
  payload: data,
});

export const getClusteringSetsReset = () => ({
  type: GET_CLUSTERING_SETS_RESET,
});

export const setSelectedClusterSet = (data) => {
  return {
    type: SET_SELECTED_CLUSTER_SET,
    payload: data,
  };
};

export const getColumnDescriptions = (data) => ({
  type: GET_COLUMN_DESCRIPTIONS,
  payload: data,
});

export const getColumnDescriptionsSuccess = (data) => ({
  type: GET_COLUMN_DESCRIPTIONS_SUCCESS,
  payload: data,
});

export const getColumnDescriptionsFailure = (data) => ({
  type: GET_COLUMN_DESCRIPTIONS_FAILURE,
  payload: data,
});

export const getColumnDescriptionsReset = () => ({
  type: GET_COLUMN_DESCRIPTIONS_RESET,
});
