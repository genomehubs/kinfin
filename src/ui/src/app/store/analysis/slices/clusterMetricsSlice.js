import { createSlice } from "@reduxjs/toolkit";

const initialState = { data: null, loading: false, error: null };

const clusterMetricsSlice = createSlice({
  name: "clusterMetrics",
  initialState,
  reducers: {
    getClusterMetrics: (state) => {
      state.loading = true;
      state.error = null;
    },
    getClusterMetricsSuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getClusterMetricsFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getClusterMetricsReset: () => initialState,
  },
});

export const {
  getClusterMetrics,
  getClusterMetricsSuccess,
  getClusterMetricsFailure,
  getClusterMetricsReset,
} = clusterMetricsSlice.actions;

export default clusterMetricsSlice.reducer;
