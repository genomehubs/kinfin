import { createSlice } from "@reduxjs/toolkit";

const initialState = { data: null, loading: false, error: null };

const attributeSummarySlice = createSlice({
  name: "attributeSummary",
  initialState,
  reducers: {
    getAttributeSummary: (state) => {
      state.loading = true;
      state.error = null;
    },
    getAttributeSummarySuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getAttributeSummaryFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getAttributeSummaryReset: () => initialState,
  },
});

export const {
  getAttributeSummary,
  getAttributeSummarySuccess,
  getAttributeSummaryFailure,
  getAttributeSummaryReset,
} = attributeSummarySlice.actions;

export default attributeSummarySlice.reducer;
