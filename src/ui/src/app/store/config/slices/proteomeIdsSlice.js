import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  loading: false,
  data: [],
  error: null,
};

const proteomeIdsSlice = createSlice({
  name: "validProteomeIds",
  initialState,
  reducers: {
    getValidProteomeIds: (state) => {
      state.loading = true;
      state.error = null;
    },
    getValidProteomeIdsSuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
    },
    getValidProteomeIdsFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    getValidProteomeIdsReset: () => initialState,
  },
});

export const {
  getValidProteomeIds,
  getValidProteomeIdsSuccess,
  getValidProteomeIdsFailure,
  getValidProteomeIdsReset,
} = proteomeIdsSlice.actions;

export default proteomeIdsSlice.reducer;
