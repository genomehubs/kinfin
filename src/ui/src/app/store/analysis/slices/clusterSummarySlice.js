import { createSlice } from "@reduxjs/toolkit";

const initialState = { data: null, loading: false, error: null };

const clusterSummarySlice = createSlice({
  name: "clusterSummary",
  initialState,
  reducers: {
    getClusterSummary: (state) => {
      state.loading = true;
      state.error = null;
    },
    getClusterSummarySuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getClusterSummaryFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getClusterSummaryReset: () => initialState,
  },
});

export const {
  getClusterSummary,
  getClusterSummarySuccess,
  getClusterSummaryFailure,
  getClusterSummaryReset,
} = clusterSummarySlice.actions;

export default clusterSummarySlice.reducer;
