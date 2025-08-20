import { configureStore } from "@reduxjs/toolkit";
import { persistReducer, persistStore } from "redux-persist";
import createSagaMiddleware from "redux-saga";
import createIndexedDBStorage from "redux-persist-indexeddb-storage";
import rootReducer from "./reducers";
import rootSaga from "./sagas";

const storage = createIndexedDBStorage("myReduxDB");
const { VITE_NODE_ENV } = import.meta.env;

const persistConfig = {
  key: "root",
  storage,
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

const sagaMiddleware = createSagaMiddleware();

const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      thunk: false,
      serializableCheck: false,
      immutableCheck: VITE_NODE_ENV !== "PRODUCTION",
    }).concat(sagaMiddleware),
  devTools: VITE_NODE_ENV !== "PRODUCTION",
});

const persistor = persistStore(store);

sagaMiddleware.run(rootSaga);

export { persistor, store };
