import { createSlice } from "@reduxjs/toolkit";

const initialState = { data: null, loading: false, error: null };

const countsByTaxonSlice = createSlice({
  name: "countsByTaxon",
  initialState,
  reducers: {
    getCountsByTaxon: (state) => {
      state.loading = true;
      state.error = null;
    },
    getCountsByTaxonSuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getCountsByTaxonFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getCountsByTaxonReset: () => initialState,
  },
});

export const {
  getCountsByTaxon,
  getCountsByTaxonSuccess,
  getCountsByTaxonFailure,
  getCountsByTaxonReset,
} = countsByTaxonSlice.actions;

export default countsByTaxonSlice.reducer;
