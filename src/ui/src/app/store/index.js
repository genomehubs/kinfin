import { persistReducer, persistStore } from "redux-persist";

import { api } from "./api";
import { configureStore } from "@reduxjs/toolkit";
import createIndexedDBStorage from "redux-persist-indexeddb-storage";
import rootReducer from "./reducers";

const storage = createIndexedDBStorage("myReduxDB");
const { VITE_NODE_ENV } = import.meta.env;

const persistConfig = {
  key: "root",
  storage,
  // Exclude RTK Query API state from persistence
  // (it manages its own cache)
  blacklist: [api.reducerPath],
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      thunk: true,
      serializableCheck: {
        // RTK Query needs to store functions and other non-serializable values
        ignoredActions: ["persist/PERSIST", "persist/REHYDRATE"],
        ignoredPaths: [api.reducerPath],
      },
      immutableCheck: VITE_NODE_ENV !== "PRODUCTION",
    }).concat(
      api.middleware,
      // middleware to help debug non-plain actions (allow thunks/functions used by RTK Query)
      () => (next) => (action) => {
        const isPlainObject =
          action !== null &&
          typeof action === "object" &&
          !Array.isArray(action);
        if (!isPlainObject) {
          console.error("Non-plain action dispatched:", action);
        }
        return next(action);
      },
    ),
  devTools: {
    trace: true,
    traceLimit: 25,
  },
});

const persistor = persistStore(store);

export { persistor, store };
