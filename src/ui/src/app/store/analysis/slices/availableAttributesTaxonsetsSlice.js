import { createSlice } from "@reduxjs/toolkit";

const initialState = { data: null, loading: false, error: null };

const availableAttributesTaxonsetsSlice = createSlice({
  name: "availableAttributesTaxonsets",
  initialState,
  reducers: {
    getAvailableAttributesTaxonsets: (state) => {
      state.loading = true;
      state.error = null;
    },
    getAvailableAttributesTaxonsetsSuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getAvailableAttributesTaxonsetsFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getAvailableAttributesTaxonsetsReset: () => {
      return initialState;
    },
  },
});

export const {
  getAvailableAttributesTaxonsets,
  getAvailableAttributesTaxonsetsSuccess,
  getAvailableAttributesTaxonsetsFailure,
  getAvailableAttributesTaxonsetsReset,
} = availableAttributesTaxonsetsSlice.actions;

export default availableAttributesTaxonsetsSlice.reducer;
