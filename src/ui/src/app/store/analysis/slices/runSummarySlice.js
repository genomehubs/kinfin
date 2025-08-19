import { createSlice } from "@reduxjs/toolkit";

const initialState = { data: null, loading: false, error: null };

const runSummarySlice = createSlice({
  name: "runSummary",
  initialState,
  reducers: {
    getRunSummary: (state) => {
      state.loading = true;
      state.error = null;
      state.data = null;
    },
    getRunSummarySuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getRunSummaryFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getRunSummaryReset: () => initialState,
  },
});

export const {
  getRunSummary,
  getRunSummarySuccess,
  getRunSummaryFailure,
  getRunSummaryReset,
} = runSummarySlice.actions;

export default runSummarySlice.reducer;
