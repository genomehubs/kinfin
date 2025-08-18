import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  data: {
    /*
    [sessionId]: {
      sessionId: "some-id",
      name: "some-name",
      clusterId: "some-id",
      clusterName: "some-name",
      config: [...],
      status: true,
      expiryDate: "2025-06-12T20:00:00Z",
    }
    */
  },
};

const configSlice = createSlice({
  name: "config",
  initialState,
  reducers: {
    storeConfig: (state, action) => {
      const { sessionId, name, config, clusterId, clusterName } =
        action.payload;
      state.data[sessionId] = {
        sessionId,
        name,
        config,
        clusterId,
        clusterName,
      };
    },
    renameConfig: (state, action) => {
      const { sessionId, newName } = action.payload;
      if (state.data[sessionId]) {
        state.data[sessionId].name = newName;
      }
    },
    deleteConfig: (state, action) => {
      delete state.data[action.payload];
    },
    updateSessionMeta: (state, action) => {
      const { sessionId, meta } = action.payload;
      if (state.data[sessionId]) {
        state.data[sessionId] = {
          ...state.data[sessionId],
          ...meta, // status, expiryDate, etc.
        };
      }
    },
    storeConfigReset: () => initialState,
  },
});

export const {
  storeConfig,
  renameConfig,
  deleteConfig,
  updateSessionMeta,
  storeConfigReset,
} = configSlice.actions;

export default configSlice.reducer;
