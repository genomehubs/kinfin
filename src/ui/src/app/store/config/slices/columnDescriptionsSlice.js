import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  data: [],
  loading: false,
  error: null,
};

const columnDescriptionsSlice = createSlice({
  name: "columnDescriptions",
  initialState,
  reducers: {
    getColumnDescriptions: (state) => {
      state.loading = true;
      state.error = null;
      state.data = [];
    },
    getColumnDescriptionsSuccess: (state, action) => {
      state.loading = false;
      state.data = action.payload;
      state.error = null;
    },
    getColumnDescriptionsFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
      state.data = [];
    },
    getColumnDescriptionsReset: () => initialState,
  },
});

export const {
  getColumnDescriptions,
  getColumnDescriptionsSuccess,
  getColumnDescriptionsFailure,
  getColumnDescriptionsReset,
} = columnDescriptionsSlice.actions;

export default columnDescriptionsSlice.reducer;
