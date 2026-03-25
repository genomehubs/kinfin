import { api } from "./api";
import { combineReducers } from "redux";
import configReducer from "./config/slices/configSlice";
// --- UI state slices (non-async Redux state) ---
import uiStateReducer from "./config/slices/uiStateSlice";

/**
 * Wrap the existing config reducer so the resulting state shape is:
 * state.config = { data: { ... }, uiState: { ... } }
 *
 * This keeps existing selectors that read `state.config.data[sessionId]`
 * working while allowing `uiState` to live under `state.config.uiState`.
 */
const configWrapper = (state = {}, action) => {
  const dataState = configReducer(state.data, action); // Pass just the data part
  const uiState = uiStateReducer(state.uiState, action);
  return {
    data: dataState, // Re-wrap under 'data' key
    uiState,
  };
};

const rootReducer = combineReducers({
  // RTK Query API reducer (keeps query cache on `state[api.reducerPath]`)
  [api.reducerPath]: api.reducer,
  config: configWrapper,
});

export default rootReducer;
