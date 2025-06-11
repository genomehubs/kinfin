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
  SET_POLLING_LOADING,
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

export const setPollingLoading = (isLoading) => ({
  type: SET_POLLING_LOADING,
  payload: isLoading,
});
