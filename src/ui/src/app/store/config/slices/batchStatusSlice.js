import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  loading: false,
  error: null,
  batchStatus: null,
};

const batchStatusSlice = createSlice({
  name: "batchStatus",
  initialState,
  reducers: {
    getBatchStatus: (state) => {
      state.loading = true;
      state.error = null;
    },
    getBatchStatusSuccess: (state, action) => {
      state.loading = false;
      state.batchStatus = action.payload;
    },
    getBatchStatusFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getBatchStatusReset: () => initialState,
  },
});

export const {
  getBatchStatus,
  getBatchStatusSuccess,
  getBatchStatusFailure,
  getBatchStatusReset,
} = batchStatusSlice.actions;

export default batchStatusSlice.reducer;
