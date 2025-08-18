import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  selectedAttributeTaxonset: null,
  selectedClusterSet: null,
  pollingLoadingBySessionId: {}, // object keyed by sessionId
  downloadLoading: {}, // object keyed by type
};

const uiStateSlice = createSlice({
  name: "uiState",
  initialState,
  reducers: {
    setSelectedAttributeTaxonset: (state, action) => {
      console.log(action);
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
