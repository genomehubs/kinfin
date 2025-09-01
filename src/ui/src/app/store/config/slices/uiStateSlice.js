import { createSlice } from "@reduxjs/toolkit";

const params = new URLSearchParams(window.location.search);

const initialState = {
  selectedAttributeTaxonset: {
    attribute: params.get("attribute") || "all",
    taxonset: params.get("taxonset") || "all",
  },
  selectedClusterSet: null,
  pollingLoadingBySessionId: {}, // object keyed by sessionId
  downloadLoading: {}, // object keyed by type
};

const uiStateSlice = createSlice({
  name: "uiState",
  initialState,
  reducers: {
    setSelectedAttributeTaxonset: (state, action) => {
      state.selectedAttributeTaxonset = action.payload;
    },
    setSelectedClusterSet: (state, action) => {
      state.selectedClusterSet = action.payload;
    },
    setPollingLoading: (state, action) => {
      const { sessionId, loading } = action.payload;
      state.pollingLoadingBySessionId[sessionId] = loading;
    },
    setDownloadLoading: (state, action) => {
      const { type, loading } = action.payload;
      state.downloadLoading[type] = loading;
    },
  },
});

export const {
  setSelectedAttributeTaxonset,
  setSelectedClusterSet,
  setPollingLoading,
  setDownloadLoading,
} = uiStateSlice.actions;

export default uiStateSlice.reducer;
