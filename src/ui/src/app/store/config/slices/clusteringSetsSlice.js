import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  loading: false,
  error: null,
  data: null,
};

const clusteringSetsSlice = createSlice({
  name: "clusteringSets",
  initialState,
  reducers: {
    getClusteringSets: (state) => {
      state.loading = true;
      state.error = null;
    },
    getClusteringSetsSuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getClusteringSetsFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getClusteringSetsReset: () => initialState,
  },
});

export const {
  getClusteringSets,
  getClusteringSetsSuccess,
  getClusteringSetsFailure,
  getClusteringSetsReset,
} = clusteringSetsSlice.actions;

export default clusteringSetsSlice.reducer;
