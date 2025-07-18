import {
  GET_RUN_SUMMARY,
  GET_RUN_SUMMARY_SUCCESS,
  GET_RUN_SUMMARY_FAILURE,
  GET_RUN_SUMMARY_RESET,
  GET_AVAILABLE_ATTRIBUTES_TAXONSETS,
  GET_AVAILABLE_ATTRIBUTES_TAXONSETS_SUCCESS,
  GET_AVAILABLE_ATTRIBUTES_TAXONSETS_FAILURE,
  GET_AVAILABLE_ATTRIBUTES_TAXONSETS_RESET,
  GET_COUNTS_BY_TAXON,
  GET_COUNTS_BY_TAXON_SUCCESS,
  GET_COUNTS_BY_TAXON_FAILURE,
  GET_COUNTS_BY_TAXON_RESET,
  GET_CLUSTER_SUMMARY,
  GET_CLUSTER_SUMMARY_SUCCESS,
  GET_CLUSTER_SUMMARY_FAILURE,
  GET_CLUSTER_SUMMARY_RESET,
  GET_ATTRIBUTE_SUMMARY,
  GET_ATTRIBUTE_SUMMARY_SUCCESS,
  GET_ATTRIBUTE_SUMMARY_FAILURE,
  GET_ATTRIBUTE_SUMMARY_RESET,
  GET_CLUSTER_METRICS,
  GET_CLUSTER_METRICS_SUCCESS,
  GET_CLUSTER_METRICS_FAILURE,
  GET_CLUSTER_METRICS_RESET,
  GET_PAIRWISE_ANALYSIS,
  GET_PAIRWISE_ANALYSIS_SUCCESS,
  GET_PAIRWISE_ANALYSIS_FAILURE,
  GET_PAIRWISE_ANALYSIS_RESET,
  GET_PLOT,
  GET_PLOT_SUCCESS,
  GET_PLOT_FAILURE,
  GET_PLOT_RESET,
} from "./actionTypes";

export const getRunSummary = (data) => ({
  type: GET_RUN_SUMMARY,
  payload: data,
});
export const getRunSummarySuccess = (data) => ({
  type: GET_RUN_SUMMARY_SUCCESS,
  payload: data,
});
export const getRunSummaryFailure = (data) => ({
  type: GET_RUN_SUMMARY_FAILURE,
  payload: data,
});
export const getRunSummaryReset = () => ({
  type: GET_RUN_SUMMARY_RESET,
});
export const getAvailableAttributesTaxonsets = (data) => ({
  type: GET_AVAILABLE_ATTRIBUTES_TAXONSETS,
  payload: data,
});
export const getAvailableAttributesTaxonsetsSuccess = (data) => ({
  type: GET_AVAILABLE_ATTRIBUTES_TAXONSETS_SUCCESS,
  payload: data,
});
export const getAvailableAttributesTaxonsetsFailure = (data) => ({
  type: GET_AVAILABLE_ATTRIBUTES_TAXONSETS_FAILURE,
  payload: data,
});
export const getAvailableAttributesTaxonsetsReset = () => ({
  type: GET_AVAILABLE_ATTRIBUTES_TAXONSETS_RESET,
});
export const getCountsByTaxon = (data) => ({
  type: GET_COUNTS_BY_TAXON,
  payload: data,
});

export const getCountsByTaxonSuccess = (data) => ({
  type: GET_COUNTS_BY_TAXON_SUCCESS,
  payload: data,
});
export const getCountsByTaxonFailure = (data) => ({
  type: GET_COUNTS_BY_TAXON_FAILURE,
  payload: data,
});
export const getCountsByTaxonReset = () => ({
  type: GET_COUNTS_BY_TAXON_RESET,
});
export const getClusterSummary = (data) => ({
  type: GET_CLUSTER_SUMMARY,
  payload: data,
});
export const getClusterSummarySuccess = (data) => ({
  type: GET_CLUSTER_SUMMARY_SUCCESS,
  payload: data,
});
export const getClusterSummaryFailure = (data) => ({
  type: GET_CLUSTER_SUMMARY_FAILURE,
  payload: data,
});
export const getClusterSummaryReset = () => ({
  type: GET_CLUSTER_SUMMARY_RESET,
});
export const getAttributeSummary = (data) => ({
  type: GET_ATTRIBUTE_SUMMARY,
  payload: data,
});
export const getAttributeSummarySuccess = (data) => ({
  type: GET_ATTRIBUTE_SUMMARY_SUCCESS,
  payload: data,
});
export const getAttributeSummaryFailure = (data) => ({
  type: GET_ATTRIBUTE_SUMMARY_FAILURE,
  payload: data,
});

export const getAttributeSummaryReset = () => ({
  type: GET_ATTRIBUTE_SUMMARY_RESET,
});
export const getClusterMetrics = (data) => ({
  type: GET_CLUSTER_METRICS,
  payload: data,
});
export const getClusterMetricsSuccess = (data) => ({
  type: GET_CLUSTER_METRICS_SUCCESS,
  payload: data,
});
export const getClusterMetricsFailure = (data) => ({
  type: GET_CLUSTER_METRICS_FAILURE,
  payload: data,
});
export const getClusterMetricsReset = () => ({
  type: GET_CLUSTER_METRICS_RESET,
});
export const getPairwiseAnalysis = (data) => ({
  type: GET_PAIRWISE_ANALYSIS,
  payload: data,
});
export const getPairwiseAnalysisSuccess = (data) => ({
  type: GET_PAIRWISE_ANALYSIS_SUCCESS,
  payload: data,
});
export const getPairwiseAnalysisFailure = (data) => ({
  type: GET_PAIRWISE_ANALYSIS_FAILURE,
  payload: data,
});
export const getPairwiseAnalysisReset = () => ({
  type: GET_PAIRWISE_ANALYSIS_RESET,
});

export const getPlot = (data) => ({
  type: GET_PLOT,
  payload: data,
});
export const getPlotSuccess = (data) => ({
  type: GET_PLOT_SUCCESS,
  payload: data,
});
export const getPlotFailure = (data) => ({
  type: GET_PLOT_FAILURE,
  payload: data,
});
export const getPlotReset = () => ({
  type: GET_PLOT_RESET,
});
