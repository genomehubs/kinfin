import configReducer, {
  getInitialState as getConfigInitialState,
} from "./config/slices/configSlice";

import { api } from "./api";
import { combineReducers } from "redux";
// --- UI state slices (non-async Redux state) ---
import uiStateReducer from "./config/slices/uiStateSlice";

/**
 * Wrap the existing config reducer so the resulting state shape is:
 * state.config = { data: { ... }, uiState: { ... } }
 *
 * This keeps existing selectors that read `state.config.data[sessionId]`
 * working while allowing `uiState` to live under `state.config.uiState`.
 */
const configWrapper = (state, action) => {
  // If no state provided, use configReducer's initial state
  if (!state) {
    const defaultConfigState = getConfigInitialState();
    const sliceState = configReducer(defaultConfigState, action);
    const uiState = uiStateReducer(undefined, action);
    return {
      data: sliceState.data,
      uiState,
    };
  }

  // Only pass the data portion to the config reducer
  const configState = { data: state.data };
  const sliceState = configReducer(configState, action);
  const uiState = uiStateReducer(state.uiState, action);
  return {
    data: sliceState.data,
    uiState,
  };
};

const rootReducer = combineReducers({
  // RTK Query API reducer (keeps query cache on `state[api.reducerPath]`)
  [api.reducerPath]: api.reducer,
  config: configWrapper,
});

export default rootReducer;
