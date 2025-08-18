import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  loading: false,
  error: null,
  data: null,
};

const analysisSlice = createSlice({
  name: "analysis",
  initialState,
  reducers: {
    initAnalysis: (state) => {
      state.loading = true;
      state.error = null;
    },
    initAnalysisSuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    initAnalysisFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    initAnalysisReset: () => initialState,
  },
});

export const {
  initAnalysis,
  initAnalysisSuccess,
  initAnalysisFailure,
  initAnalysisReset,
} = analysisSlice.actions;

export default analysisSlice.reducer;
