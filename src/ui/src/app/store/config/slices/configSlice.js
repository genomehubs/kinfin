import { createSlice } from "@reduxjs/toolkit";

const STORAGE_KEY = "__kinfin_sessions";

// Load persistent sessions from localStorage
const loadPersistedSessions = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch (e) {
    console.warn("Failed to load persisted sessions:", e);
    return {};
  }
};

// Save session configs to localStorage
const persistSessions = (sessions) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (e) {
    console.warn("Failed to persist sessions:", e);
  }
};

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
    ...loadPersistedSessions(),
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
        linkouts,
        meta = {},
      } = action.payload;
      if (!sessionId) return;
      // state contains { data: {...} }
      if (!state || typeof state !== "object") {
        return;
      }

      // Get existing entry if it exists
      const existing = state.data[sessionId];

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
        ...(linkouts !== undefined && { linkouts }),
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
      state.data[sessionId] = newEntry;

      // Persist lightweight metadata to localStorage (excluding config)
      const lightweight = {
        sessionId: newEntry.sessionId,
        name: newEntry.name,
        clusterId: newEntry.clusterId,
        clusterName: newEntry.clusterName,
        linkouts: newEntry.linkouts,
        status: newEntry.status,
        expiryDate: newEntry.expiryDate,
      };

      // Get all persisted sessions and update/add this one
      try {
        const allSessions = JSON.parse(
          localStorage.getItem(STORAGE_KEY) || "{}",
        );
        allSessions[sessionId] = lightweight;
        persistSessions(allSessions);
      } catch (e) {
        console.warn("Failed to persist session metadata:", e);
      }
    },
    deleteConfig: (state, action) => {
      if (!state || typeof state !== "object") return;
      const sessionId = action.payload;
      delete state.data[sessionId];

      // Remove from persisted sessions in localStorage
      try {
        const allSessions = JSON.parse(
          localStorage.getItem(STORAGE_KEY) || "{}",
        );
        delete allSessions[sessionId];
        persistSessions(allSessions);
      } catch (e) {
        console.warn("Failed to update persisted sessions:", e);
      }
    },
    updateSessionMeta: (state, action) => {
      const { sessionId, meta } = action.payload;
      if (!state || typeof state !== "object") return;
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
  deleteConfig,
  updateSessionMeta,
  storeConfigReset,
} = configSlice.actions;

export const getInitialState = () => {
  // Reload persisted sessions from localStorage each time initialState is needed
  return {
    data: {
      ...loadPersistedSessions(),
    },
  };
};

export default configSlice.reducer;
