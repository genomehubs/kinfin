import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  loading: false,
  error: null,
  status: null,
};

const runStatusSlice = createSlice({
  name: "runStatus",
  initialState,
  reducers: {
    getRunStatus: (state) => {
      state.loading = true;
      state.error = null;
    },
    getRunStatusSuccess: (state, action) => {
      state.loading = false;
      state.status = action.payload;
    },
    getRunStatusFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getRunStatusReset: () => initialState,
  },
});

export const {
  getRunStatus,
  getRunStatusSuccess,
  getRunStatusFailure,
  getRunStatusReset,
} = runStatusSlice.actions;

export default runStatusSlice.reducer;
