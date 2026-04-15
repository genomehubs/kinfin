import { api } from "./api";
import { configureStore } from "@reduxjs/toolkit";
import rootReducer from "./reducers";

const { VITE_NODE_ENV } = import.meta.env;

const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      thunk: true,
      serializableCheck: {
        // RTK Query needs to store functions and other non-serializable values
        ignoredActions: [],
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
export { store };
