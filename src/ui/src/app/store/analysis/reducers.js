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

const initialState = {
  runSummary: { data: null, loading: false, error: null },
  availableAttributesTaxonsets: { data: null, loading: false, error: null },
  countsByTaxon: { data: null, loading: false, error: null },
  clusterSummary: { data: null, loading: false, error: null },
  attributeSummary: { data: null, loading: false, error: null },
  clusterMetrics: { data: null, loading: false, error: null },
  pairwiseAnalysis: { data: null, loading: false, error: null },
  plot: {
    data: { allRarefactionCurve: null, clusterSizeDistribution: null },
    loading: false,
    error: null,
  },
};

const analysisReducer = (state = initialState, action) => {
  switch (action.type) {
    case GET_RUN_SUMMARY:
      return {
        ...state,
        runSummary: { data: null, loading: true, error: null },
      };
    case GET_RUN_SUMMARY_SUCCESS:
      return {
        ...state,
        runSummary: { data: action.payload, loading: false, error: null },
      };
    case GET_RUN_SUMMARY_FAILURE:
      return {
        ...state,
        runSummary: { data: null, loading: false, error: action.payload },
      };
    case GET_RUN_SUMMARY_RESET:
      return { ...state, runSummary: initialState.runSummary };
    case GET_AVAILABLE_ATTRIBUTES_TAXONSETS:
      return {
        ...state,
        availableAttributesTaxonsets: {
          data: null,
          loading: true,
          error: null,
        },
      };
    case GET_AVAILABLE_ATTRIBUTES_TAXONSETS_SUCCESS:
      return {
        ...state,
        availableAttributesTaxonsets: {
          data: action.payload,
          loading: false,
          error: null,
        },
      };
    case GET_AVAILABLE_ATTRIBUTES_TAXONSETS_FAILURE:
      return {
        ...state,
        availableAttributesTaxonsets: {
          data: null,
          loading: false,
          error: action.payload,
        },
      };
    case GET_AVAILABLE_ATTRIBUTES_TAXONSETS_RESET:
      return {
        ...state,
        availableAttributesTaxonsets: initialState.availableAttributesTaxonsets,
      };
    case GET_COUNTS_BY_TAXON:
      return {
        ...state,
        countsByTaxon: { data: null, loading: true, error: null },
      };
    case GET_COUNTS_BY_TAXON_SUCCESS:
      return {
        ...state,
        countsByTaxon: { data: action.payload, loading: false, error: null },
      };
    case GET_COUNTS_BY_TAXON_FAILURE:
      return {
        ...state,
        countsByTaxon: { data: null, loading: false, error: action.payload },
      };
    case GET_COUNTS_BY_TAXON_RESET:
      return { ...state, countsByTaxon: initialState.countsByTaxon };
    case GET_CLUSTER_SUMMARY:
      return {
        ...state,
        clusterSummary: { ...state.clusterSummary, loading: true, error: null },
      };
    case GET_CLUSTER_SUMMARY_SUCCESS:
      return {
        ...state,
        clusterSummary: { data: action.payload, loading: false, error: null },
      };
    case GET_CLUSTER_SUMMARY_FAILURE:
      return {
        ...state,
        clusterSummary: { data: null, loading: false, error: action.payload },
      };
    case GET_CLUSTER_SUMMARY_RESET:
      return { ...state, clusterSummary: initialState.clusterSummary };
    case GET_ATTRIBUTE_SUMMARY:
      return {
        ...state,
        attributeSummary: {
          ...state.attributeSummary,
          loading: true,
          error: null,
        },
      };
    case GET_ATTRIBUTE_SUMMARY_SUCCESS:
      return {
        ...state,
        attributeSummary: { data: action.payload, loading: false, error: null },
      };
    case GET_ATTRIBUTE_SUMMARY_FAILURE:
      return {
        ...state,
        attributeSummary: { data: null, loading: false, error: action.payload },
      };
    case GET_ATTRIBUTE_SUMMARY_RESET:
      return { ...state, attributeSummary: initialState.attributeSummary };
    case GET_CLUSTER_METRICS:
      return {
        ...state,
        clusterMetrics: { ...state.clusterMetrics, loading: true, error: null },
      };
    case GET_CLUSTER_METRICS_SUCCESS:
      return {
        ...state,
        clusterMetrics: { data: action.payload, loading: false, error: null },
      };
    case GET_CLUSTER_METRICS_FAILURE:
      return {
        ...state,
        clusterMetrics: { data: null, loading: false, error: action.payload },
      };
    case GET_CLUSTER_METRICS_RESET:
      return { ...state, clusterMetrics: initialState.clusterMetrics };
    case GET_PAIRWISE_ANALYSIS:
      return {
        ...state,
        pairwiseAnalysis: { data: null, loading: true, error: null },
      };
    case GET_PAIRWISE_ANALYSIS_SUCCESS:
      return {
        ...state,
        pairwiseAnalysis: { data: action.payload, loading: false, error: null },
      };
    case GET_PAIRWISE_ANALYSIS_FAILURE:
      return {
        ...state,
        pairwiseAnalysis: { data: null, loading: false, error: action.payload },
      };
    case GET_PAIRWISE_ANALYSIS_RESET:
      return { ...state, pairwiseAnalysis: initialState.pairwiseAnalysis };
    case GET_PLOT:
      return { ...state, plot: { data: null, loading: true, error: null } };
    case GET_PLOT_SUCCESS:
      return {
        ...state,
        plot: { data: action.payload, loading: false, error: null },
      };
    case GET_PLOT_FAILURE:
      return {
        ...state,
        plot: { data: null, loading: false, error: action.payload },
      };
    case GET_PLOT_RESET:
      return { ...state, plot: initialState.plot };
    default:
      return state;
  }
};

export default analysisReducer;
