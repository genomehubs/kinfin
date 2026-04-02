import { createSlice } from "@reduxjs/toolkit";

import { getInitialUrlSearchParams } from "#utils/getInitialUrlSearchParams";

const params = getInitialUrlSearchParams();

const initialState = {
  selectedAttributeTaxonset: {
    attribute: params.get("attribute") || "all",
    taxonset: params.get("taxonset") || "all",
  },
  selectedClusterSet: null,
  pollingLoadingBySessionId: {}, // object keyed by sessionId
  downloadLoading: {}, // object keyed by type
  columnSettings: {}, // object keyed by tableKey -> settings object/array
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
    setColumnSettings: (state, action) => {
      const { tableKey, settings } = action.payload;
      state.columnSettings[tableKey] = settings;
    },
  },
});

export const {
  setSelectedAttributeTaxonset,
  setSelectedClusterSet,
  setPollingLoading,
  setDownloadLoading,
  setColumnSettings,
} = uiStateSlice.actions;

export default uiStateSlice.reducer;
