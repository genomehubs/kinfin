import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  data: { rarefactionCurve: null, clusterSizeDistribution: null },
  loading: false,
  error: null,
};

const plotSlice = createSlice({
  name: "plot",
  initialState,
  reducers: {
    getPlot: (state) => {
      state.loading = true;
      state.error = null;
    },
    getPlotSuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getPlotFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getPlotReset: () => initialState,
  },
});

export const { getPlot, getPlotSuccess, getPlotFailure, getPlotReset } =
  plotSlice.actions;

export default plotSlice.reducer;
