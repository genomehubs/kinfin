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

const initialState = {
  initAnalysis: { data: null, loading: false, error: null },
  runStatus: { data: null, loading: false, error: null },
  selectedAttributeTaxonset: { attribute: "all", taxonset: "all" },
  storeConfig: {
    data: {},
  },
  pollingLoading: false,
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
      const { sessionId, name, config } = action.payload;
      const existingData = state.storeConfig?.data || {};
      return {
        ...state,
        storeConfig: {
          ...state.storeConfig,
          data: {
            ...existingData,
            [sessionId]: { sessionId, name, config },
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
    case SET_POLLING_LOADING:
      return {
        ...state,
        pollingLoading: action.payload,
      };

    default:
      return state;
  }
};

export default configReducer;
