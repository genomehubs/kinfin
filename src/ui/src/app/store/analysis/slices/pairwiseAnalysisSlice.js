import { createSlice } from "@reduxjs/toolkit";

const initialState = { data: null, loading: false, error: null };

const pairwiseAnalysisSlice = createSlice({
  name: "pairwiseAnalysis",
  initialState,
  reducers: {
    getPairwiseAnalysis: (state) => {
      state.loading = true;
      state.error = null;
    },
    getPairwiseAnalysisSuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getPairwiseAnalysisFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getPairwiseAnalysisReset: () => initialState,
  },
});

export const {
  getPairwiseAnalysis,
  getPairwiseAnalysisSuccess,
  getPairwiseAnalysisFailure,
  getPairwiseAnalysisReset,
} = pairwiseAnalysisSlice.actions;

export default pairwiseAnalysisSlice.reducer;
