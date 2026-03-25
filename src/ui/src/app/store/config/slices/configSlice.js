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
      const {
        sessionId,
        name,
        config,
        clusterId,
        clusterName,
        meta = {},
      } = action.payload;
      if (!sessionId) return;
      // state here is just the 'data' object (see configWrapper in reducers.js)
      if (!state || typeof state !== "object") {
        return;
      }

      // Get existing entry if it exists
      const existing = state[sessionId];

      // Build the new entry: start with existing data, override with provided values, update meta
      // This preserves previously stored data when updates don't include all fields
      const newEntry = {
        sessionId,
        // Preserve existing values, override with explicitly provided (non-undefined) ones
        ...(existing || {}),
        ...(name !== undefined && { name }),
        ...(config !== undefined && { config }),
        ...(clusterId !== undefined && { clusterId }),
        ...(clusterName !== undefined && { clusterName }),
        // Meta fields are always updated
        ...meta,
      };

      // Avoid unnecessary writes/updates when the stored entry is identical
      try {
        if (existing) {
          const existingStr = JSON.stringify(existing);
          const newStr = JSON.stringify(newEntry);
          if (existingStr === newStr) {
            return;
          }
        }
      } catch (e) {
        // Fallback: if stringify fails for some reason, proceed to write
        console.warn(
          "Failed to stringify config for comparison, proceeding with update",
          e,
        );
      }

      // Store the merged entry
      state[sessionId] = newEntry;
    },
    renameConfig: (state, action) => {
      const { sessionId, newName } = action.payload;
      if (!state || typeof state !== "object") return;
      if (state[sessionId]) {
        state[sessionId].name = newName;
      }
    },
    deleteConfig: (state, action) => {
      if (!state || typeof state !== "object") return;
      delete state[action.payload];
    },
    updateSessionMeta: (state, action) => {
      const { sessionId, meta } = action.payload;
      if (!state || typeof state !== "object") return;
      if (state[sessionId]) {
        state[sessionId] = {
          ...state[sessionId],
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
