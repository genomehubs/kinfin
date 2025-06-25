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
} from "./actionTypes";

const initialState = {
  initAnalysis: { data: null, loading: false, error: null },
  runStatus: { data: null, loading: false, error: null },
  selectedAttributeTaxonset: { attribute: "all", taxonset: "all" },
  storeConfig: {
    data: {
      /*
    [sessionId]: {
      sessionId: "some-id",
      name: "some-name",
      clusterId: "some-id",
      clusterName: "some-name",
      config: [...],
      status: true,
      expiryDate: "2025-06-12T20:00:00Z",
    }
    */
    },
  },
  validProteomeIds: { data: null, loading: false, error: null },
  pollingLoading: {},
  batchStatus: { data: null, loading: false, error: null },
  clusteringSets: { data: null, loading: false, error: null },
  selectedClusterSet: null,
};

const configReducer = (state = initialState, action) => {
  switch (action.type) {
    case INIT_ANALYSIS:
      return {
        ...state,
        initAnalysis: { data: null, loading: true, error: null },
      };
    case INIT_ANALYSIS_SUCCESS:
      return {
        ...state,
        initAnalysis: { data: action.payload, loading: false, error: null },
      };
    case INIT_ANALYSIS_FAILURE:
      return {
        ...state,
        initAnalysis: { data: null, loading: false, error: action.payload },
      };
    case INIT_ANALYSIS_RESET:
      return { ...state, initAnalysis: initialState.initAnalysis };

    case GET_RUN_STATUS:
      return {
        ...state,
        runStatus: { data: null, loading: true, error: null },
      };
    case GET_RUN_STATUS_SUCCESS:
      return {
        ...state,
        runStatus: { data: action.payload, loading: false, error: null },
      };
    case GET_RUN_STATUS_FAILURE:
      return {
        ...state,
        runStatus: { data: null, loading: false, error: action.payload },
      };
    case GET_RUN_STATUS_RESET:
      return { ...state, runStatus: initialState.runStatus };

    case SET_SELECTED_ATTRIBUTE_TAXONSET:
      return {
        ...state,
        selectedAttributeTaxonset: {
          attribute: action.payload.attribute,
          taxonset: action.payload.taxonset,
        },
      };

    case STORE_CONFIG: {
      const { sessionId, name, config, clusterId, clusterName } =
        action.payload;
      const existingData = state.storeConfig?.data || {};
      return {
        ...state,
        storeConfig: {
          ...state.storeConfig,
          data: {
            ...existingData,
            [sessionId]: { sessionId, name, config, clusterId, clusterName },
          },
        },
      };
    }
    case RENAME_CONFIG: {
      const { sessionId, newName } = action.payload;
      const existing = state.storeConfig.data || {};
      if (!existing[sessionId]) {
        return state;
      }

      return {
        ...state,
        storeConfig: {
          ...state.storeConfig,
          data: {
            ...existing,
            [sessionId]: {
              ...existing[sessionId],
              name: newName,
            },
          },
        },
      };
    }
    case DELETE_CONFIG: {
      const sessionId = action.payload;
      const { [sessionId]: _, ...remaining } = state.storeConfig.data || {};
      return {
        ...state,
        storeConfig: {
          ...state.storeConfig,
          data: remaining,
        },
      };
    }

    case STORE_CONFIG_RESET:
      return {
        ...state,
        storeConfig: {
          data: {},
        },
      };
    case GET_VALID_PROTEOME_IDS:
      return {
        ...state,
        validProteomeIds: { data: null, loading: true, error: null },
      };

    case GET_VALID_PROTEOME_IDS_SUCCESS:
      return {
        ...state,
        validProteomeIds: { data: action.payload, loading: false, error: null },
      };

    case GET_VALID_PROTEOME_IDS_FAILURE:
      return {
        ...state,
        validProteomeIds: { data: null, loading: false, error: action.payload },
      };

    case GET_VALID_PROTEOME_IDS_RESET:
      return {
        ...state,
        validProteomeIds: initialState.validProteomeIds,
      };
    case SET_POLLING_LOADING:
      return {
        ...state,
        pollingLoadingBySessionId: {
          ...state.pollingLoadingBySessionId,
          [action.payload.sessionId]: action.payload.loading,
        },
      };
    case GET_BATCH_STATUS:
      return {
        ...state,
        batchStatus: { data: null, loading: true, error: null },
      };

    case GET_BATCH_STATUS_SUCCESS:
      return {
        ...state,
        batchStatus: { data: action.payload, loading: false, error: null },
      };

    case GET_BATCH_STATUS_FAILURE:
      return {
        ...state,
        batchStatus: { data: null, loading: false, error: action.payload },
      };

    case GET_BATCH_STATUS_RESET:
      return {
        ...state,
        batchStatus: initialState.batchStatus,
      };
    case UPDATE_SESSION_META: {
      const { sessionId, meta } = action.payload;
      const existing = state.storeConfig.data || {};
      if (!existing[sessionId]) {
        return state;
      }

      return {
        ...state,
        storeConfig: {
          ...state.storeConfig,
          data: {
            ...existing,
            [sessionId]: {
              ...existing[sessionId],
              ...meta, // this allows updating status, expiryDate, etc.
            },
          },
        },
      };
    }
    case GET_CLUSTERING_SETS:
      return {
        ...state,
        clusteringSets: { data: null, loading: true, error: null },
      };

    case GET_CLUSTERING_SETS_SUCCESS:
      return {
        ...state,
        clusteringSets: { data: action.payload, loading: false, error: null },
      };

    case GET_CLUSTERING_SETS_FAILURE:
      return {
        ...state,
        clusteringSets: { data: null, loading: false, error: action.payload },
      };

    case GET_CLUSTERING_SETS_RESET:
      return {
        ...state,
        clusteringSets: initialState.clusteringSets,
      };
    case SET_SELECTED_CLUSTER_SET:
      return { ...state, selectedClusterSet: action.payload };

    default:
      return state;
  }
};

export default configReducer;
