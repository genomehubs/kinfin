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
  GET_CLUSTERING_SETS,
  GET_CLUSTERING_SETS_SUCCESS,
  GET_CLUSTERING_SETS_FAILURE,
  GET_CLUSTERING_SETS_RESET,
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

export const getValidProteomeIds = (data) => ({
  type: GET_VALID_PROTEOME_IDS,
  payload: data,
});

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
